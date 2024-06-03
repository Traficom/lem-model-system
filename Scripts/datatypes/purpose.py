from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast
from collections import defaultdict
import numpy # type: ignore
import pandas
from datahandling.resultdata import ResultsData
from datahandling.zonedata import ZoneData

import utils.log as log
import parameters.zone as param
import models.logit as logit
from parameters.assignment import assignment_classes, vot_inv, vot_classes
from pathlib import Path
import json
import openmatrix as omx
import models.generation as generation
from datatypes.demand import Demand
from datatypes.histogram import TourLengthHistogram


class Purpose:
    """Generic container class without methods.
    
    Sets the purpose zone bounds.

    Parameters
    ----------
    specification : dict
        "name" : str
            Tour purpose name
        "orig" : str
            Origin of the tours
        "dest" : str
            Destination of the tours
        "area" : str
            Model area
        "impedance_share" : dict
            Impedance shares
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultsData (optional)
        Writer object to result directory
    """
    distance: numpy.ndarray

    def __init__(self, 
                 specification: Dict[str,Optional[str]], 
                 zone_data: ZoneData, 
                 resultdata: Optional[ResultsData]=None):
        self.name = specification["name"]
        self.orig = specification["orig"]
        self.dest = specification["dest"]
        self.area = specification["area"]
        self.impedance_share = specification["impedance_share"]
        self.demand_share = specification["demand_share"]
        self.impedance_transform = specification["impedance_transform"]
        self.name = cast(str, self.name) #type checker help
        self.area = cast(str, self.area) #type checker help
        zone_numbers = zone_data.all_zone_numbers
        zone_intervals = param.purpose_areas[self.area]
        self.bounds = slice(*zone_numbers.searchsorted(
            [zone_intervals[0], zone_intervals[-1]]))
        sub_intervals = zone_numbers[self.bounds].searchsorted(zone_intervals)
        self.sub_bounds = [slice(sub_intervals[i-1], sub_intervals[i])
            for i in range(1, len(sub_intervals))]
        self.sub_intervals = sub_intervals[1:]
        self.zone_data = zone_data
        self.resultdata = resultdata
        self.generated_tours: Dict[str, numpy.array] = {}
        self.attracted_tours: Dict[str, numpy.array] = {}

    @property
    def zone_numbers(self):
        return self.zone_data.zone_numbers[self.bounds]

    @property
    def dest_interval(self):
        return slice(0, self.zone_data.nr_zones)

    def transform_impedance(self, impedance):
        """Perform transformation from time period dependent matrices
        to aggregate impedance matrices for specific travel purpose.

        Parameters
        ----------
        impedance: dict
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

        Return
        ------
        dict
            key : str
                Mode (car/transit/bike/walk)
            value : dict
                key : str
                    Type (time/cost/dist)
                value : numpy 2-d matrix
                    Impedance (float 2-d matrix)
        """
        rows = self.bounds
        cols = self.dest_interval
        mapping = self.zone_data.aggregations.municipality_centre_mapping
        day_imp = {}
        long_dist_modes = {"train": "j_first_mile", "long_d_bus": "e_first_mile", "airplane": "l_first_mile"}
        for mode in self.impedance_share:
            day_imp[mode] = defaultdict(float)
            ass_class = mode.replace("pax", assignment_classes[self.name])
            for time_period in self.impedance_share[mode]:
                for mtx_type in impedance[time_period]:
                    if ass_class in impedance[time_period][mtx_type]:
                        share = self.impedance_share[mode][time_period]
                        imp = impedance[time_period][mtx_type][ass_class]
                        day_imp[mode][mtx_type] += share[0] * imp[rows, cols]
                        day_imp[mode][mtx_type] += share[1] * imp[cols, rows].T
            if mode in long_dist_modes:
                day_imp[long_dist_modes[mode]] = defaultdict(float)
                if mode == "train":
                    day_imp[long_dist_modes[mode].replace("mile", "taxi")] = defaultdict(float)
                ass_class = [long_dist_modes[mode], long_dist_modes[mode].replace("mile", "taxi")]
                for time_period in self.impedance_share[mode]:
                    for mtx_type in impedance[time_period]:
                        if mtx_type != "loc_fboard":
                            if ass_class[0] in impedance[time_period][mtx_type]:
                                share = self.impedance_share[mode][time_period]
                                imp_fm = impedance[time_period][mtx_type][ass_class[0]]
                                day_imp[long_dist_modes[mode]][mtx_type] += share[0] * imp_fm[rows, cols] *2
                            if ass_class[1] in impedance[time_period][mtx_type]:
                                share = self.impedance_share[mode][time_period]
                                imp_fm = impedance[time_period][mtx_type][ass_class[1]]
                                day_imp[long_dist_modes[mode].replace("mile", "taxi")][mtx_type] += share[0] * imp_fm[rows, cols] *2
            if "vrk" in impedance:
                for mtx_type in day_imp[mode]:
                    day_imp[mode][mtx_type] = day_imp[mode][mtx_type][:, mapping]
        # Apply cost change to validate model elasticities
        if self.zone_data.mtx_adjustment is not None:
            for idx, row in self.zone_data.mtx_adjustment.iterrows():
                try:
                    t = row["mtx_type"]
                    m = row["mode"]
                    p = row["cost_change"]
                    day_imp[m][t] = p * day_imp[m][t]
                    msg = (f"Demand calculation {self.name}: " 
                           + f"Added {round(100*(p-1))} % to {t} : {m}.")
                    log.warn(msg)
                except KeyError:
                    pass
        for mode in self.impedance_transform:
            for mtx_type in self.impedance_transform[mode]:
                p = self.impedance_transform[mode][mtx_type]
                day_imp[mode][mtx_type] *= p
        return day_imp


def new_tour_purpose(specification, zone_data, resultdata):
    """Create purpose for two-way tour or for secondary destination of tour.

    Parameters
    ----------
    specification : dict
        "name" : str
            Tour purpose name (hw/oo/hop/sop/...)
        "orig" : str
            Origin of the tours (home/source)
        "dest" : str
            Destination of the tours (work/other/source/...)
        "area" : str
            Model area (metropolitan/peripheral)
        "struct" : str
            Model structure (dest>mode/mode>dest)
        "impedance_share" : dict
            Impedance shares
        "impedance_transform" : dict
            Impedance transformations
        "destination_choice" : dict
            Destionation choice parameters
        "mode_choice" dict
            Mode choice parameters
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object for result directory
    """
    args = (specification, zone_data, resultdata)
    purpose = (SecDestPurpose(*args) if "sec_dest" in specification
                else TourPurpose(*args))
    try:
        purpose.sources = specification["source"]
    except KeyError:
        pass
    return purpose


class TourPurpose(Purpose):
    """Standard two-way tour purpose.

    Parameters
    ----------
    specification : dict
        See `new_tour_purpose()`
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object for result directory
    """

    def __init__(self, specification, zone_data, resultdata):
        args = (self, specification, zone_data, resultdata)
        Purpose.__init__(*args)
        if self.orig == "source":
            self.gen_model = generation.NonHomeGeneration(self, resultdata)
        else:
            self.gen_model = generation.GenerationModel(self, resultdata)
        if self.name == "sop":
            self.model = logit.OriginModel(*args)
        elif specification["struct"] == "dest>mode":
            self.model = logit.DestModeModel(*args)
        else:
            self.model = logit.ModeDestModel(*args)
            self.accessibility_model = logit.AccessibilityModel(*args)
        for mode in self.demand_share:
            self.demand_share[mode]["vrk"] = [1, 1]
        self.modes = list(self.model.mode_choice_param)
        self.histograms = {mode: TourLengthHistogram(self.name)
            for mode in self.modes}
        self.mapping = self.zone_data.aggregations.mappings[
            param.purpose_matrix_aggregation_level]
        self.aggregates = {}
        self.own_zone_demand = {}
        self.sec_dest_purpose = None

    @property
    def dist(self):
        return self.distance[self.bounds, self.dest_interval]

    def print_data(self):
        self.resultdata.print_data(
            pandas.Series(
                sum(self.generated_tours.values()), self.zone_numbers,
                name=self.name),
            "generation.txt")
        self.resultdata.print_data(
            pandas.Series(
                sum(self.attracted_tours.values()),
                self.zone_data.zone_numbers, name=self.name),
            "attraction.txt")
        demsums = {mode: self.generated_tours[mode].sum()
            for mode in self.modes}
        demand_all = float(sum(demsums.values()))
        mode_shares = pandas.concat(
            {self.name: pandas.Series(
                {mode: demsums[mode] / demand_all for mode in demsums},
                name="mode_share")},
            names=["purpose", "mode"])
        self.resultdata.print_concat(mode_shares, "mode_share.txt")
        self.resultdata.print_concat(
            pandas.concat(
                {m: self.histograms[m].histogram for m in self.histograms},
                names=["mode", "purpose", "interval"]),
            "trip_lengths.txt")
        self.resultdata.print_matrices(
            self.aggregates, "aggregated_demand", self.name)
        for mode in self.aggregates:
            self.resultdata.print_data(
                self.own_zone_demand[mode], "own_zone_demand.txt")

    def init_sums(self):
        agg = self.mapping.drop_duplicates()
        for mode in self.modes:
            self.generated_tours[mode] = numpy.zeros_like(self.zone_numbers)
            self.attracted_tours[mode] = numpy.zeros_like(self.zone_data.zone_numbers)
            self.histograms[mode].__init__(self.name)
            self.aggregates[mode] = pandas.DataFrame(0, agg, agg)
            self.own_zone_demand[mode] = pandas.Series(
                0, self.zone_numbers, name="{}_{}".format(self.name, mode))

    def calc_prob(self, impedance, is_last_iteration):
        """Calculate mode and destination probabilities.
        
        Parameters
        ----------
        impedance : dict
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2d matrix
        """
        purpose_impedance = self.transform_impedance(impedance)
        self.prob = self.model.calc_prob(purpose_impedance)
        if is_last_iteration and self.name[0] != 's':
            self.accessibility_model.calc_accessibility(
                purpose_impedance)
            
        access_modes = {}
        long_dist_modes = {"train": "j_first_mile", "long_d_bus": "e_first_mile", "airplane": "l_first_mile"}

        if "long" in self.name:
            for mode in long_dist_modes:
                utility = numpy.zeros_like(next(iter(next(iter(purpose_impedance.values())).values())))
                split_probs = self.split_connection_mode(purpose_impedance, self.prob[mode], mode, long_dist_modes[mode], utility)
                access_modes[long_dist_modes[mode]] = split_probs["car"]
                access_modes[mode] = split_probs["transit"]
                if mode == "train":
                    access_modes["j_first_taxi"] = split_probs["car_pax"]
        self.prob.update(access_modes)
        if is_last_iteration and self.name[0] != 's':
            self.accessibility_model.calc_accessibility(
                purpose_impedance)
    
    def split_connection_mode(self, impedance, prob_main_mode, pt_mode, fm_mode, utility):
        expsum = numpy.zeros_like(utility)
        exps = {}
        fm_utils = {}
        split_probs = {}
        access_modes = ("car", "transit") if pt_mode == "long_d_bus" else ("car", "car_pax", "transit")
        for mode in access_modes:
            utility = numpy.zeros_like(expsum)
            parameters = self.get_acc_model_parameters(mode, pt_mode)
            self._add_impedance(utility, parameters["b"], impedance, mode, pt_mode, fm_mode, parameters["scale_param"], parameters["scale_correction"], parameters["acc_fac"])
            self._add_constant(utility, parameters["b"], mode, parameters["scale_param"], parameters["scale_correction"])
            utility = self._add_zone_util(utility.T, parameters["b"], parameters["scale_param"], parameters["scale_correction"], generation=True).T
            fm_utils[mode] = utility
            exps[mode] = numpy.exp(utility)
            del utility
            expsum = expsum + exps[mode]
        
        #utils_file = omx.open_file("C:/Users/kuivavee/Documents/Matrices/utils.omx","a")
        #shares_file = omx.open_file("C:/Users/kuivavee/Documents/Matrices/shares.omx","a")
        #for a_mode in access_modes:
        #    util_ = fm_utils[a_mode]
        #    utils_file[pt_mode + "_" + a_mode + "_" + self.name][:] = util_
        #    del util_
        #    shares_file[pt_mode + "_" + a_mode + "_" + self.name][:] = exps[a_mode]/expsum
        #    if a_mode == "car_pax" and pt_mode != "train":
        #        split_probs["car"] = split_probs["car"] + exps[a_mode]/expsum * prob_main_mode
        #    else:
        #        split_probs[a_mode] = exps[a_mode]/expsum * prob_main_mode
        #utils_file.close()
        #no_local_pt_ratio = numpy.maximum(numpy.zeros_like(impedance[pt_mode]["loc_fboard"]), numpy.ones_like(impedance[pt_mode]["loc_fboard"]) - impedance[pt_mode]["loc_fboard"]/10)#- impedance[pt_mode]["loc_rboard"])/ 5
        #shares_file[pt_mode + "_" + "walk" + "_" + self.name][:] = no_local_pt_ratio * shares_file[pt_mode + "_" + "transit" + "_" + self.name]
        #shares_file[pt_mode + "_" + "transit" + "_" + self.name][:] -= no_local_pt_ratio * shares_file[pt_mode + "_" + "transit" + "_" + self.name]
        #shares_file.close()

        return split_probs
    
    def _add_constant(self, utility, b, mode, scale_param, scale_correction):
        #scale_param = 5
        nest_param = b["mode_acc"]["log"]["logsum"]
        if mode == "walk":
            const = 0
        else:
            try:
                const = b["mode_acc"]["constant"] * scale_param / nest_param
            except (TypeError, ValueError):
                const = b["mode_acc"]["constant"][0] * scale_param / nest_param
        if mode == "car":
            const -= 6
        if mode == "car_pax":
            const -= 0
        if mode == "transit":
            const += 3
        try: # If only one parameter
            utility += const
        except ValueError: # Separate sub-region parameters
            for i, bounds in enumerate(self.sub_bounds):
                if utility.ndim == 1: # 1-d array calculation
                        utility[bounds] += const[i]
                else: # 2-d matrix calculation
                        utility[bounds, :] += const[i]
    
    def _add_zone_util(self, utility, b, scale_param_carown, scale_correction, generation=False):
        nest_param = b["mode_acc"]["log"]["logsum"]
        zdata = self.zone_data
        for i in b["mode_acc"]["generation"]:
            try: # If only one parameter
                utility += b["mode_acc"]["generation"][i] * zdata.get_data(i, self.bounds, generation) * scale_param_carown / nest_param
            except ValueError: # Separate sub-region parameters
                for j, bounds in enumerate(self.sub_bounds):
                    data = zdata.get_data(i, bounds, generation)
                    if utility.ndim == 1: # 1-d array calculation
                        utility[bounds] += data  * b["mode_acc"]["generation"][i] * scale_param_carown / nest_param
                    else: # 2-d matrix calculation
                        utility[bounds, :] += data  * b["mode_acc"]["generation"][i] * scale_param_carown / nest_param
        return utility

    def pnr_cost_by_purpose_duration(self, cost, perc_bcost, actual_bcost, fm_mode, remove_pnr_cost=0):
        pnr_duration = {"j_first_mile": {"avg": 1.98, "business": 0.99, "leisure": 2.89, "work": 1.22},
                        "e_first_mile": {"avg": 1.98, "business": 0.99, "leisure": 2.89, "work": 1.22},
                        "l_first_mile": {"avg": 2.78, "business": 2.65, "leisure": 3.30, "work": 1.27}}
        pnr_cost_24h = (perc_bcost-actual_bcost*vot_inv[vot_classes[fm_mode]])/(vot_inv[vot_classes[fm_mode]]*(pnr_duration[fm_mode]["avg"]-2))
        cost -= pnr_cost_24h
        if not remove_pnr_cost:
            cost += pnr_cost_24h*pnr_duration[fm_mode][self.name[3:-5]]
        return cost

    def _add_impedance(self, utility, b, impedance, acc_mode, pt_mode, fm_mode, scale_param, scale_correction, acc_fac):
        mode = pt_mode if acc_mode == "transit" else fm_mode
        if acc_mode == "car_pax" and mode == "j_first_mile":
            mode == "j_first_taxi"
        if acc_mode == "car":
            impedance[mode]["cost"] = self.pnr_cost_by_purpose_duration(impedance[mode]["cost"], impedance[mode]["perc_bcost"], impedance[mode]["board_cost"], mode, 0)
        if acc_mode == "car_pax" and fm_mode == "l_first_mile":
            impedance[mode]["cost"] = self.pnr_cost_by_purpose_duration(impedance[mode]["cost"], impedance[mode]["perc_bcost"], impedance[mode]["board_cost"], mode, 1)
        
        b_t_main = b["dest_main"]["impedance"]["time"] * scale_correction * scale_param / acc_fac[pt_mode]
        b_c_main = b["dest_main"]["impedance"]["cost"] * scale_correction * scale_param
        b_t_transit = b["dest_transit_acc"]["impedance"]["time"] * scale_param
        b_t_acc = b["dest_acc"]["impedance"]["time"] * scale_param

        utility += b_t_main*(impedance[mode]["total_time"] - impedance[mode]["loc_time"] - impedance[mode]["loc_btime"] - impedance[mode]["aux_time"])
        aux_time = 1.75*(impedance[mode]["aux_time"]-impedance[mode]["car_time"]) if acc_mode != "transit" else 1.75*impedance[mode]["aux_time"]
        utility += b_c_main * impedance[mode]["cost"]
        if acc_mode == "car":
            utility += b_c_main * 0.12 * impedance[mode]["car_dist"]
        utility += b_t_acc * impedance[mode]["car_time"] / 3 + b_t_transit * (impedance[mode]["loc_btime"] + impedance[mode]["loc_time"] + aux_time)
        
        return utility
            
    def get_acc_model_parameters(self, acc_mode, pt_mode):
        parameters_path = Path(__file__).parent.parent / "parameters" / "demand"
        print(self.name)
        for file in parameters_path.rglob(self.name[:-5] + ".json"):
            param_short = json.loads(file.read_text("utf-8"))
        for file in parameters_path.rglob(self.name[:-5].replace('h','w') + ".json"):
            param_short = json.loads(file.read_text("utf-8"))
        for file in parameters_path.rglob(self.name + ".json"):
            param_mainmode = json.loads(file.read_text("utf-8"))
        b_mode_acc: Optional[Dict[str, Dict[str, Any]]] = param_short["mode_choice"][acc_mode + (self.name[2:-5].replace("business", "work") if acc_mode != "car_pax" else "")]
        b_dest_acc: Dict[str, Dict[str, Any]] = param_short["destination_choice"][acc_mode + (self.name[2:-5].replace("business", "work") if acc_mode != "car_pax" else "")]
        b_dest_transit_acc: Dict[str, Dict[str, Any]] = param_short["destination_choice"]["transit" + self.name[2:-5].replace("business", "work")]
        b_dest_main: Dict[str, Dict[str, Any]] = param_mainmode["destination_choice"][pt_mode]
        b = {"mode_acc": b_mode_acc, "dest_acc":  b_dest_acc, "dest_main": b_dest_main, "dest_transit_acc": b_dest_transit_acc}
        scale_param = 1
        if "business" not in self.name:
            scale_correction = b["dest_transit_acc"]["impedance"]["cost"] / b["dest_main"]["impedance"]["cost"]
        else:
            scale_correction = b["dest_transit_acc"]["impedance"]["time"] / b["dest_main"]["impedance"]["time"]
        if self.name == "hb_business_long":
            acc_fac = {"train": 1.18, "long_d_bus": 1, "airplane": 1}
        else:
            acc_fac = {"train": 1.36, "long_d_bus": 1.36, "airplane": 1.36}
        return {"b": b, "scale_param": scale_param, "scale_correction": scale_correction, "acc_fac": acc_fac}

    def calc_basic_prob(self, impedance, is_last_iteration):
        """Calculate mode and destination probabilities.

        Individual dummy variables are not included.

        Parameters
        ----------
        impedance : dict
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2d matrix
        """
        purpose_impedance = self.transform_impedance(impedance)
        self.model.calc_basic_prob(purpose_impedance)
        if is_last_iteration and self.name[0] != 's':
            self.accessibility_model.calc_accessibility(
                purpose_impedance)

    def calc_demand(self):
        """Calculate purpose specific demand matrices.
              
        Returns
        -------
        dict
            Mode (car/transit/bike) : dict
                Demand matrix for whole day : Demand
        """
        tours = self.gen_model.get_tours()
        demand = {}
        agg = self.zone_data.aggregations
        for mode in self.modes:
            mtx = (self.prob.pop(mode) * tours).T
            try:
                self.sec_dest_purpose.gen_model.add_tours(mtx, mode, self)
            except AttributeError:
                pass
            demand[mode] = Demand(self, mode, mtx)
            self.attracted_tours[mode] = mtx.sum(0)
            self.generated_tours[mode] = mtx.sum(1)
            self.histograms[mode].count_tour_dists(mtx, self.dist)
            self.aggregates[mode] = agg.aggregate_mtx(
                pandas.DataFrame(
                    mtx, self.zone_numbers, self.zone_data.zone_numbers),
                self.mapping.name)
            self.own_zone_demand[mode] = pandas.Series(
                numpy.diag(mtx), self.zone_numbers,
                name="{}_{}".format(self.name, mode))
        return demand


class SecDestPurpose(Purpose):
    """Purpose for secondary destination of tour.

    Parameters
    ----------
    specification : dict
        See `new_tour_purpose()`
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object to result directory
    """

    def __init__(self, specification, zone_data, resultdata):
        args = (self, specification, zone_data, resultdata)
        Purpose.__init__(*args)
        self.gen_model = generation.SecDestGeneration(self, resultdata)
        self.model = logit.SecDestModel(*args)
        self.modes = list(self.model.dest_choice_param)
        for mode in self.demand_share:
            self.demand_share[mode]["vrk"] = [[0.5, 0.5], [0.5, 0.5]]

    @property
    def dest_interval(self):
        return self.bounds

    def init_sums(self):
        for mode in self.model.dest_choice_param:
            self.generated_tours[mode] = numpy.zeros_like(self.zone_numbers)
        for purpose in self.gen_model.param:
            for mode in self.gen_model.param[purpose]:
                self.attracted_tours[mode] = numpy.zeros_like(
                    self.zone_data.zone_numbers, float)

    def generate_tours(self):
        """Generate the source tours without secondary destinations."""
        self.tours = {}
        self.init_sums()
        for mode in self.model.dest_choice_param:
            self.tours[mode] = self.gen_model.get_tours(mode)

    def distribute_tours(self, mode, impedance, orig, orig_offset=0):
        """Decide the secondary destinations for all tours (generated 
        earlier) starting from one specific zone.
        
        Parameters
        ----------
        mode : str
            Mode (car/transit/bike)
        impedance : dict
            Type (time/cost/dist) : numpy 2d matrix
        orig : int
            The relative zone index from which these tours origin
        orig_offset : int (optional)
            Absolute zone index of orig is orig_offset + orig

        Returns
        -------
        Demand
            Matrix of destination -> secondary_destination pairs
            The origin zone for all of these tours
        """
        generation = self.tours[mode][orig, :]
        # All o-d pairs below threshold are neglected,
        # total demand is increased for other pairs.
        dests = generation > param.secondary_destination_threshold
        if not dests.any():
            # If no o-d pairs have demand above threshold,
            # the sole destination with largest demand is picked
            dests = [generation.argmax()]
            generation.fill(0)
            generation[dests] = generation.sum()
        else:
            generation[dests] *= generation.sum() / generation[dests].sum()
            generation[~dests] = 0
        prob = self.calc_prob(mode, impedance, orig, dests)
        demand = numpy.zeros_like(impedance["time"])
        demand[dests, :] = (prob * generation[dests]).T
        self.attracted_tours[mode][self.bounds] += demand.sum(0)
        return Demand(self, mode, demand, orig_offset + orig)

    def calc_prob(self, mode, impedance, orig, dests):
        """Calculate secondary destination probabilites.
        
        For tours starting in specific zone and ending in some zones.
        
        Parameters
        ----------
        mode : str
            Mode (car/transit/bike)
        impedance : dict
            Type (time/cost/dist) : numpy 2d matrix
        orig : int
            Origin zone index
        dests : list or boolean array
            Destination zone indices

        Returns
        -------
        numpy.ndarray
            Probability matrix for chosing zones as secondary destination
        """
        dest_imp = {}
        for mtx_type in impedance:
            dest_imp[mtx_type] = (impedance[mtx_type][dests, :]
                                  + impedance[mtx_type][:, orig]
                                  - impedance[mtx_type][dests, orig][:, numpy.newaxis])
        return self.model.calc_prob(mode, dest_imp, orig, dests)

    def print_data(self):
        self.resultdata.print_data(
            pandas.Series(
                sum(self.attracted_tours.values()),
                self.zone_data.zone_numbers, name=self.name),
            "attraction.txt")
