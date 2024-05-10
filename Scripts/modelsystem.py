import threading
import multiprocessing
import os
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Set, Union, cast
import numpy # type: ignore
import pandas
import random
from collections import defaultdict
from assignment.abstract_assignment import AssignmentModel
from assignment.emme_assignment import EmmeAssignmentModel
from assignment.mock_assignment import MockAssignmentModel

import utils.log as log
from utils.divide_matrices import divide_matrices
import assignment.departure_time as dt
from datahandling.resultdata import ResultsData
from datahandling.zonedata import ZoneData, BaseZoneData
from datahandling.matrixdata import MatrixData
from demand.freight import FreightModel
from demand.trips import DemandModel
from demand.external import ExternalModel
from datatypes.purpose import new_tour_purpose
from datatypes.purpose import Purpose, SecDestPurpose
from datatypes.person import Person
from datatypes.tour import Tour
from models.linear import CarDensityModel
import parameters.assignment as param
import parameters.zone as zone_param
import parameters.tour_generation as gen_param


class ModelSystem:
    """Object keeping track of all sub-models and tasks in model system.
    
    Parameters
    ----------
    zone_data_path : str
        Directory path where input data for forecast year are found
    base_zone_data_path : str
        Directory path where input data for base year are found
    base_matrices_path : str
        Directory path where base demand matrices are found
    results_path : str
        Directory path where to store results
    assignment_model : assignment.abstract_assignment.AssignmentModel
        Assignment model wrapper used in model runs,
        can be EmmeAssignmentModel or MockAssignmentModel
    submodel: str
        Name of submodel, used for choosing appropriate zone mapping
    """

    def __init__(self,
                 zone_data_path: Path,
                 base_zone_data_path: Path,
                 base_matrices_path: Path,
                 results_path: Path,
                 assignment_model: AssignmentModel,
                 submodel: str):
        self.ass_model = cast(Union[MockAssignmentModel,EmmeAssignmentModel], assignment_model) #type checker hint
        self.zone_numbers: numpy.array = self.ass_model.zone_numbers

        # Input data
        self.zdata_base = BaseZoneData(
            base_zone_data_path, self.zone_numbers, f"{submodel}.zmp")
        self.basematrices = MatrixData(base_matrices_path / submodel)
        self.long_dist_matrices = MatrixData(base_matrices_path / "koko_suomi")
        self.zdata_forecast = ZoneData(
            zone_data_path, self.zone_numbers, self.zdata_base.aggregations,
            f"{submodel}.zmp")

        # Output data
        self.resultdata = ResultsData(results_path)
        self.resultmatrices = MatrixData(results_path / "Matrices" / submodel)
        parameters_path = Path(__file__).parent / "parameters" / "demand"
        home_based_purposes = []
        sec_dest_purposes = []
        other_purposes = []
        for file in parameters_path.rglob("*.json"):
            purpose = new_tour_purpose(
                json.loads(file.read_text("utf-8")), self.zdata_forecast,
                self.resultdata)
            if (sorted(next(iter(purpose.impedance_share.values())))
                    == sorted(assignment_model.time_periods)):
                if isinstance(purpose, SecDestPurpose):
                    sec_dest_purposes.append(purpose)
                elif purpose.orig == "home":
                    home_based_purposes.append(purpose)
                else:
                    other_purposes.append(purpose)
        self.dm = self._init_demand_model(
            home_based_purposes + other_purposes + sec_dest_purposes)
        self.travel_modes = {mode: True for purpose in self.dm.tour_purposes
            for mode in purpose.modes}  # Dict instead of set, to preserve order
        self.em = ExternalModel(
            self.basematrices, self.zdata_forecast, self.zone_numbers)
        self.mode_share: List[Dict[str,Any]] = []
        self.convergence = pandas.DataFrame()

    def _init_demand_model(self, tour_purposes: List[Purpose]):
        return DemandModel(
            self.zdata_forecast, self.resultdata, tour_purposes,
            is_agent_model=False)

    def _add_internal_demand(self, previous_iter_impedance, is_last_iteration):
        """Produce mode-specific demand matrices.

        Add them for each time-period to container in departure time model.

        Parameters
        ----------
        previous_iter_impedance : dict
            key : str
                Time period (aht/pt/iht)
            value : dict
                key : str
                    Impedance type (time/cost/dist)
                value : dict
                    key : str
                        Assignment class (car_work/transit/...)
                    value : numpy.ndarray
                        Impedance (float 2-d matrix)
        is_last_iteration : bool (optional)
            If this is the last iteration, 
            secondary destinations are calculated for all modes
        """
        log.info("Demand calculation started...")

        # Mode and destination probability matrices are calculated first,
        # as logsums from probability calculation are used in tour generation.
        self.dm.create_population_segments()
        for purpose in self.dm.tour_purposes:
            if isinstance(purpose, SecDestPurpose):
                purpose.gen_model.init_tours()
            else:
                purpose.calc_prob(previous_iter_impedance, is_last_iteration)
        
        # Tour generation
        self.dm.generate_tours()
        
        for purpose in self.dm.tour_purposes:
            if isinstance(purpose, SecDestPurpose):
                purpose_impedance = purpose.transform_impedance(
                    previous_iter_impedance)
        previous_iter_impedance.clear()

        # Assigning of tours to mode, destination and time period
        for purpose in self.dm.tour_purposes:
            if isinstance(purpose, SecDestPurpose):
                purpose.generate_tours()
                if is_last_iteration:
                    for mode in purpose.model.dest_choice_param:
                        self._distribute_sec_dests(
                            purpose, mode, purpose_impedance)
                else:
                    self._distribute_sec_dests(
                        purpose, "car_leisure", purpose_impedance)
            else:
                if purpose.name != "wh":
                    demand = purpose.calc_demand()
                if purpose.dest != "source":
                    for mode in demand:
                        self.dtm.add_demand(demand[mode])
        log.info("Demand calculation completed")

    # possibly merge with init
    def assign_base_demand(self, 
            is_end_assignment: bool = False) -> Dict[str, Dict[str, numpy.ndarray]]:
        """Assign base demand to network (before first iteration).

        Parameters
        ----------
        is_end_assignment : bool (optional)
            If base demand is assigned without demand calculations

        Returns
        -------
        dict
            key : str
                Assignment class (car/transit/bike/walk)
            value : dict
                key : str
                    Impedance type (time/cost/dist)
                value : numpy.ndarray
                    Impedance (float 2-d matrix)
        """
        impedance = {}

        # create attributes and background variables to network
        self.ass_model.prepare_network(self.zdata_forecast.car_dist_cost)
        self.dtm = dt.DirectDepartureTimeModel(self.ass_model)

        if not self.ass_model.use_free_flow_speeds:
            self.ass_model.init_assign()
        self.ass_model.calc_transit_cost(self.zdata_forecast.transit_zone)
        Purpose.distance = self.ass_model.beeline_dist
        with self.resultmatrices.open(
                "beeline", "", self.ass_model.zone_numbers, m="w") as mtx:
            mtx["all"] = Purpose.distance

        # Perform traffic assignment and get result impedance, 
        # for each time period
        for ap in self.ass_model.assignment_periods:
            tp = ap.name
            log.info("Assigning period {}...".format(tp))
            if not self.ass_model.use_free_flow_speeds:
                # If we want to assign all trips with traffic congestion
                long_dist_classes = (param.car_classes
                                     + param.long_distance_transit_classes
                                     + param.freight_classes)
                try:
                    # Try getting long-distance trips from separate files
                    cm = self.long_dist_matrices.open(
                        "demand", tp, self.ass_model.zone_numbers,
                        long_dist_classes)
                    mtx = cm.__enter__()
                except IOError:
                    # Otherwise long-distance trips must be in base matrices
                    cm = self.basematrices.open(
                        "demand", tp, self.ass_model.zone_numbers,
                        long_dist_classes)
                    mtx = cm.__enter__()
                for ass_class in long_dist_classes:
                    self.dtm.demand[tp][ass_class] = mtx[ass_class]
                cm.__exit__(None, None, None)
                short_dist_classes = (param.private_classes
                                      + param.local_transit_classes)
                with self.basematrices.open(
                        "demand", tp, self.ass_model.zone_numbers,
                        short_dist_classes) as mtx:
                    for ass_class in short_dist_classes:
                        self.dtm.demand[tp][ass_class] += mtx[ass_class]
            elif is_end_assignment:
                # If we only assign long-distance trip matrices
                long_dist_classes = (param.car_classes
                                     + param.long_distance_transit_classes)
                with self.basematrices.open(
                        "demand", tp, self.ass_model.zone_numbers,
                        long_dist_classes) as mtx:
                    for ass_class in long_dist_classes:
                        self.dtm.demand[tp][ass_class] = mtx[ass_class]
            ap.assign_trucks_init()
            impedance[tp] = (ap.end_assign() if is_end_assignment
                             else ap.assign(self.travel_modes))
            if tp == self.ass_model.time_periods[0]:
                for mode, mtx in impedance[tp]["dist"].items():
                    divide_matrices(
                        mtx, Purpose.distance, f"Network/beeline dist {mode}")
            if is_end_assignment:
                self._save_to_omx(impedance[tp], tp)
        if is_end_assignment:
            self.ass_model.aggregate_results(self.resultdata)
            self._calculate_noise_areas()
            self.resultdata.flush()
        self.dtm.calc_gaps()
        return impedance

    def run_iteration(self, previous_iter_impedance, iteration=None):
        """Calculate demand and assign to network.

        Parameters
        ----------
        previous_iter_impedance : dict
            key : str
                Assignment class (car/transit/bike/walk)
            value : dict
                key : str
                    Impedance type (time/cost/dist)
                value : numpy.ndarray
                    Impedance (float 2-d matrix)
        iteration : int or str (optional)
            Iteration number (0, 1, 2, ...) or "last"
            If this is the last iteration, 
            secondary destinations are calculated for all modes,
            congested assignment is performed,
            and matrix and assignment results are printed.
        Returns
        -------
        dict
            key : str
                Assignment class (car/transit/bike/walk)
            value : dict
                key : str
                    Impedance type (time/cost/dist)
                value : numpy.ndarray
                    Impedance (float 2-d matrix)
        """
        impedance = {}
        self.dtm.init_demand(
            [mode for mode in self.travel_modes if mode != "walk"])

        # Update car density
        prediction = (self.zdata_base["car_density"][:self.zdata_base.nr_zones]
                      .clip(upper=1.0))
        self.zdata_forecast["car_density"] = prediction
        self.zdata_forecast["cars_per_1000"] = 1000 * prediction

        # Calculate internal demand
        self._add_internal_demand(previous_iter_impedance, iteration=="last")

        # Calculate external demand
        for mode in param.external_modes:
            int_demand = self._sum_trips_per_zone(mode)
            ext_demand = self.em.calc_external(mode, int_demand)
            self.dtm.add_demand(ext_demand)

        # Calculate tour sums and mode shares
        tour_sum = {mode: self._sum_trips_per_zone(mode, include_dests=False)
            for mode in self.travel_modes}
        sum_all = sum(tour_sum.values())
        mode_shares = {}
        agg = self.zdata_base.aggregations
        for mode in tour_sum:
            self.resultdata.print_data(
                tour_sum[mode], "origins_demand.txt", mode)
            for area_type in agg.mappings:
                self.resultdata.print_data(
                    agg.aggregate_array(tour_sum[mode], area_type),
                    f"origins_demand_{area_type}.txt", mode)
            self.resultdata.print_data(
                tour_sum[mode] / sum_all, "origins_shares.txt", mode)
            mode_shares[mode] = tour_sum[mode].sum() / sum_all.sum()
        self.mode_share.append(mode_shares)
        trip_sum = {mode: self._sum_trips_per_zone(mode)
            for mode in self.travel_modes}
        for mode in tour_sum:
            for area_type in agg.mappings:
                self.resultdata.print_data(
                    agg.aggregate_array(trip_sum[mode], area_type),
                    f"trips_{area_type}.txt", mode)
        self.resultdata.print_line("\nAssigned demand", "result_summary")
        self.resultdata.print_line(
            "\t" + "\t".join(param.transport_classes), "result_summary")

        # Add vans and save demand matrices
        for ap in self.ass_model.assignment_periods:
            self.dtm.add_vans(ap.name, self.zdata_forecast.nr_zones)
            if (iteration=="last"
                    and not isinstance(self.ass_model, MockAssignmentModel)):
                self._save_demand_to_omx(ap.name)

        # Calculate and return traffic impedance
        for ap in self.ass_model.assignment_periods:
            tp = ap.name
            log.info("Assigning period " + tp)
            impedance[tp] = (ap.end_assign() if iteration=="last"
                             else ap.assign(self.travel_modes))
            if iteration=="last":
                self._save_to_omx(impedance[tp], tp)
        if iteration=="last":
            self.ass_model.aggregate_results(
                self.resultdata,
                self.zdata_base.aggregations.municipality_mapping)
            self._calculate_noise_areas()
            self._calculate_accessibility_and_savu_zones()
            self.resultdata.print_line("\nMode shares", "result_summary")
            for mode in mode_shares:
                self.resultdata.print_line(
                    "{}\t{:1.2%}".format(mode, mode_shares[mode]),
                    "result_summary")

        # Reset time-period specific demand matrices (DTM),
        # and empty result buffer
        gap = self.dtm.calc_gaps()
        log.info("Demand model convergence in iteration {} is {:1.5f}".format(
            iteration, gap["rel_gap"]))
        self.convergence = self.convergence.append(gap, ignore_index=True)
        self.resultdata._df_buffer["demand_convergence.txt"] = self.convergence
        self.resultdata.flush()
        return impedance

    def _save_demand_to_omx(self, tp):
        zone_numbers = self.ass_model.zone_numbers
        demand_sum_string = tp
        with self.resultmatrices.open("demand", tp, zone_numbers, m='w') as mtx:
            for ass_class in param.transport_classes:
                demand = self.dtm.demand[tp][ass_class]
                mtx[ass_class] = demand
                demand_sum_string += "\t{:8.0f}".format(demand.sum())
        self.resultdata.print_line(demand_sum_string, "result_summary")
        log.info("Saved demand matrices for " + str(tp))

    def _save_to_omx(self, impedance, tp):
        zone_numbers = self.ass_model.zone_numbers
        for mtx_type in impedance:
            with self.resultmatrices.open(mtx_type, tp, zone_numbers, m='w') as mtx:
                for ass_class in impedance[mtx_type]:
                    mtx[ass_class] = impedance[mtx_type][ass_class]

    def _calculate_noise_areas(self):
        noise_areas = self.ass_model.calc_noise(
            self.zdata_base.aggregations.municipality_mapping)
        self.resultdata.print_data(noise_areas, "noise_areas.txt", "area")
        pop = self.zdata_base.aggregations.aggregate_array(
            self.zdata_forecast["population"], "area")
        conversion = pandas.Series(zone_param.pop_share_per_noise_area)
        noise_pop = conversion * noise_areas * pop
        self.resultdata.print_data(noise_pop, "noise_areas.txt", "population")

    def _calculate_accessibility_and_savu_zones(self):
        logsum = 0
        sust_logsum = 0
        car_logsum = 0
        for purpose in self.dm.tour_purposes:
            if (purpose.area == "metropolitan" and purpose.orig == "home"
                    and purpose.dest != "source"
                    and not isinstance(purpose, SecDestPurpose)):
                zone_numbers = purpose.zone_numbers
                bounds = purpose.bounds
                weight = gen_param.tour_generation[purpose.name]["population"]
                logsum += weight * purpose.access
                sust_logsum += weight * purpose.sustainable_access
                car_logsum += weight * purpose.car_access
        pop = self.zdata_forecast["population"][bounds]
        self.resultdata.print_line(
            "\nTotal accessibility:\t{:1.2f}".format(
                numpy.average(logsum, weights=pop)),
            "result_summary")
        self.resultdata.print_data(logsum, "accessibility.txt", "all")
        avg_sust_logsum = numpy.average(sust_logsum, weights=pop)
        self.resultdata.print_line(
            "Sustainable accessibility:\t{:1.2f}".format(avg_sust_logsum),
            "result_summary")
        self.resultdata.print_data(
            sust_logsum, "sustainable_accessibility.txt", "all")
        self.resultdata.print_data(car_logsum, "car_accessibility.txt", "all")
        intervals = zone_param.savu_intervals
        savu = numpy.searchsorted(intervals, sust_logsum) + 1
        self.resultdata.print_data(
            pandas.Series(savu, zone_numbers), "savu.txt", "savu_zone")
        avg_savu = numpy.searchsorted(intervals, avg_sust_logsum) + 1
        avg_savu += ((avg_sust_logsum - intervals[avg_savu-2])
                     / (intervals[avg_savu-1] - intervals[avg_savu-2]))
        self.resultdata.print_line(
            "Average SAVU:\t{:1.4f}".format(avg_savu),
            "result_summary")

    def _sum_trips_per_zone(self, mode, include_dests=True):
        int_demand = pandas.Series(0, self.zdata_base.zone_numbers)
        for purpose in self.dm.tour_purposes:
            if mode in purpose.modes and purpose.dest != "source":
                bounds = (next(iter(purpose.sources)).bounds
                    if isinstance(purpose, SecDestPurpose)
                    else purpose.bounds)
                int_demand[bounds] += purpose.generated_tours[mode]
                if include_dests:
                    int_demand += purpose.attracted_tours[mode]
        return int_demand

    def _distribute_sec_dests(self, purpose, mode, impedance):
        threads = []
        demand = []
        nr_threads = param.performance_settings["number_of_processors"]
        if nr_threads == "max":
            nr_threads = multiprocessing.cpu_count()
        elif nr_threads <= 0:
            nr_threads = 1
        bounds = next(iter(purpose.sources)).bounds
        for i in range(nr_threads):
            # Take a range of origins, for which this thread
            # will calculate secondary destinations
            origs = range(i, bounds.stop - bounds.start, nr_threads)
            # Results will be saved in a temp dtm, to avoid memory clashes
            dtm = dt.DepartureTimeModel(
                self.ass_model.nr_zones, self.ass_model.time_periods, [mode])
            demand.append(dtm)
            thread = threading.Thread(
                target=self._distribute_tours,
                args=(dtm, purpose, mode, impedance, origs))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        for dtm in demand:
            for tp in dtm.demand:
                for ass_class in dtm.demand[tp]:
                    self.dtm.demand[tp][ass_class] += dtm.demand[tp][ass_class]
        purpose.print_data()

    def _distribute_tours(self, container, purpose, mode, impedance, origs):
        for orig in origs:
            demand = purpose.distribute_tours(mode, impedance[mode], orig)
            container.add_demand(demand)

    def _update_ratios(self, impedance, tp):
        """Calculate time and cost ratios.
        
        Parameters
        ----------
        impedance : dict
            Impedance matrices.
        tp : str
            Time period (usually aht in this function).
        """ 
        car_time = numpy.ma.average(
            impedance["time"]["car_work"], axis=1,
            weights=self.dtm.demand[tp]["car_work"])
        transit_time = numpy.ma.average(
            impedance["time"]["transit_work"], axis=1,
            weights=self.dtm.demand[tp]["transit_work"])
        time_ratio = transit_time / car_time
        time_ratio = time_ratio.clip(0.01, None)
        self.resultdata.print_data(
            pandas.Series(time_ratio, self.zone_numbers),
            "impedance_ratio.txt", "time")
        self.zdata_forecast["time_ratio"] = pandas.Series(
            numpy.ma.getdata(time_ratio), self.zone_numbers)
        car_cost = numpy.ma.average(
            impedance["cost"]["car_work"], axis=1,
            weights=self.dtm.demand[tp]["car_work"])
        transit_cost = numpy.ma.average(
            impedance["cost"]["transit_work"], axis=1,
            weights=self.dtm.demand[tp]["transit_work"])
        cost_ratio = transit_cost / 44. / car_cost
        cost_ratio = cost_ratio.clip(0.01, None)
        self.resultdata.print_data(
            pandas.Series(cost_ratio, self.zone_numbers),
            "impedance_ratio.txt", "cost")
        self.zdata_forecast["cost_ratio"] = pandas.Series(
            numpy.ma.getdata(cost_ratio), self.zone_numbers)


class AgentModelSystem(ModelSystem):
    """Object keeping track of all sub-models and tasks in agent model system.

    Agents are added one-by-one to departure time model,
    where they are (so far) split in deterministic fractions.
    
    Parameters
    ----------
    zone_data_path : str
        Directory path where input data for forecast year are found
    base_zone_data_path : str
        Directory path where input data for base year are found
    base_matrices_path : str
        Directory path where base demand matrices are found
    results_path : str
        Directory path where to store results
    assignment_model : assignment.abstract_assignment.AssignmentModel
        Assignment model wrapper used in model runs,
        can be EmmeAssignmentModel or MockAssignmentModel
    name : str
        Name of scenario, used for results subfolder
    """

    def _init_demand_model(self, tour_purposes: List[Purpose]):
        log.info("Creating synthetic population")
        random.seed(zone_param.population_draw)
        return DemandModel(
            self.zdata_forecast, self.resultdata, tour_purposes,
            is_agent_model=True)

    def _add_internal_demand(self, previous_iter_impedance, is_last_iteration):
        """Produce tours and add fractions of them
        for each time-period to container in departure time model.

        Parameters
        ----------
        previous_iter_impedance : dict
            key : str
                Time period (aht/pt/iht)
            value : dict
                key : str
                    Impedance type (time/cost/dist)
                value : dict
                    key : str
                        Assignment class (car_work/transit/...)
                    value : numpy.ndarray
                        Impedance (float 2-d matrix)
        is_last_iteration : bool (optional)
            If this is the last iteration, 
            secondary destinations are calculated for all modes
        """
        log.info("Demand calculation started...")
        random.seed(None)
        self.dm.car_use_model.calc_basic_prob()
        for purpose in self.dm.tour_purposes:
            if isinstance(purpose, SecDestPurpose):
                purpose.init_sums()
            else:
                if (purpose.area == "peripheral" or purpose.dest == "source"
                        or purpose.name == "oop"):
                    purpose.calc_prob(
                        previous_iter_impedance, is_last_iteration)
                    purpose.gen_model.init_tours()
                    purpose.gen_model.add_tours()
                    demand = purpose.calc_demand()
                    if purpose.dest != "source":
                        for mode in demand:
                            self.dtm.add_demand(demand[mode])
                else:
                    purpose.init_sums()
                    purpose.calc_basic_prob(
                        previous_iter_impedance, is_last_iteration)
        tour_probs = self.dm.generate_tour_probs()
        log.info("Assigning mode and destination for {} agents ({} % of total population)".format(
            len(self.dm.population), int(zone_param.agent_demand_fraction*100)))
        purpose = self.dm.purpose_dict["hoo"]
        sec_dest_tours = {mode: [defaultdict(list) for _ in purpose.zone_numbers]
            for mode in purpose.modes}
        # Add keys for work-tour-related modes (e.g., "car_work"),
        # which refer to the same demand containers as for leisure tours.
        # They are all assigned as leisure trips.
        work_tours = {mode.replace("leisure", "work"): sec_dest_tours[mode]
                      for mode in sec_dest_tours}
        sec_dest_tours.update(work_tours)
        car_users = pandas.Series(
            0, self.zdata_forecast.zone_numbers[self.dm.car_use_model.bounds])
        for person in self.dm.population:
            person.decide_car_use()
            car_users[person.zone.number] += person.is_car_user
            person.add_tours(self.dm.purpose_dict, tour_probs)
            for tour in person.tours:
                tour.choose_mode(person.is_car_user)
                tour.choose_destination(sec_dest_tours)
        for purpose in self.dm.tour_purposes:
            try:
                purpose.model.cumul_dest_prob.clear()
            except AttributeError:
                pass
        self.dm.car_use_model.print_results(
            car_users / self.dm.zone_population, self.dm.zone_population)
        log.info("Primary destinations assigned")
        purpose = self.dm.purpose_dict["hoo"]
        purpose_impedance = purpose.transform_impedance(
            previous_iter_impedance)
        nr_threads = param.performance_settings["number_of_processors"]
        if nr_threads == "max":
            nr_threads = multiprocessing.cpu_count()
        elif nr_threads <= 0:
            nr_threads = 1
        bounds = next(iter(purpose.sources)).bounds
        modes = purpose.modes if is_last_iteration else ["car_leisure"]
        for mode in modes:
            threads = []
            for i in range(nr_threads):
                origs = range(i, bounds.stop - bounds.start, nr_threads)
                thread = threading.Thread(
                    target=self._distribute_tours,
                    args=(
                        mode, origs, sec_dest_tours[mode],
                        purpose_impedance[mode]))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
        for purpose in self.dm.tour_purposes:
            purpose.print_data()
        if is_last_iteration:
            random.seed(zone_param.population_draw)
            self.dm.predict_income()
            random.seed(None)
            fname0 = "agents"
            fname1 = "tours"
            # print person and tour attr to files
            self.resultdata.print_line("\t".join(Person.attr), fname0)
            self.resultdata.print_line("\t".join(Tour.attr), fname1)
            for person in self.dm.population:
                person.calc_income()
                self.resultdata.print_line(str(person), fname0)
                for tour in person.tours:
                    tour.calc_cost(previous_iter_impedance)
                    self.resultdata.print_line(str(tour), fname1)
            log.info("Results printed to files {} and {}".format(
                fname0, fname1))
        previous_iter_impedance.clear()
        dtm = dt.DepartureTimeModel(
            self.ass_model.nr_zones, self.ass_model.time_periods,
            self.travel_modes)
        for person in self.dm.population:
            for tour in person.tours:
                dtm.add_demand(tour)
        for tp in dtm.demand:
            for ass_class in dtm.demand[tp]:
                self.dtm.demand[tp][ass_class] = dtm.demand[tp][ass_class]
        log.info("Demand calculation completed")

    def _distribute_tours(self, mode, origs, sec_dest_tours, impedance):
        sec_dest_purpose = self.dm.purpose_dict["hoo"]
        for orig in origs:
                dests = list(sec_dest_tours[orig])
                probs = sec_dest_purpose.calc_prob(
                    mode, impedance, orig, dests).cumsum(axis=0)
                for j, dest in enumerate(dests):
                    for tour in sec_dest_tours[orig][dest]:
                        tour.choose_secondary_destination(probs[:, j])
