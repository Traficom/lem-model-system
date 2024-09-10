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
from parameters.assignment import vot_inv, vot_classes, assignment_classes, aux_transit_time
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
        intermodals = {"train": "j_first_mile", "long_d_bus": "e_first_mile", "airplane": "l_first_mile"}
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

            # For intermodal assignment classes, private-public-sequences' impedance is duplicated and used as round-trip impedance. This way, public-private-sequences need not be assigned in other than end assignments.
            if mode in intermodals:
                day_imp[intermodals[mode]] = defaultdict(float)
                if mode == "train":
                    day_imp[intermodals[mode].replace("mile", "taxi")] = defaultdict(float)
                intermodal_ass_class = [intermodals[mode], intermodals[mode].replace("mile", "taxi")] # Intermodal classes are named as "mile" for first-mile, "taxi" is used only for train assignment with no parking costs.
                for time_period in self.impedance_share[mode]:
                    for mtx_type in impedance[time_period]:
                        if intermodal_ass_class[0] in impedance[time_period][mtx_type]:
                            share = self.impedance_share[mode][time_period]
                            imp_fm = impedance[time_period][mtx_type][intermodal_ass_class[0]]
                            day_imp[intermodals[mode]][mtx_type] += share[0] * imp_fm[rows, cols] *2
                        if intermodal_ass_class[1] in impedance[time_period][mtx_type]:
                            share = self.impedance_share[mode][time_period]
                            imp_fm = impedance[time_period][mtx_type][intermodal_ass_class[1]]
                            day_imp[intermodals[mode].replace("mile", "taxi")][mtx_type] += share[0] * imp_fm[rows, cols] *2
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
        
        #If the trip is long-distance, calculate unimodal/intermodal probability split for each main mode
        if "long" in self.name:
            access_splits = {}
            intermodals = {"train": "j_first_mile", "long_d_bus": "e_first_mile", "airplane": "l_first_mile"}
            for mode in intermodals:
                utility = numpy.zeros_like(next(iter(next(iter(purpose_impedance.values())).values())))
                access_splits[mode] = self.split_connection_mode(purpose_impedance, mode, intermodals[mode], utility)
                
        # Calculate main mode probability after access mode probability to have access mode logsum as variable
        self.prob = self.model.calc_prob(purpose_impedance)
        if is_last_iteration and self.name[0] != 's':
            self.accessibility_model.calc_accessibility(
                purpose_impedance)
            
        # If the trip is long-distance, calculate joint main mode/access mode - probability for each intermodal class in EMME assignment
        if "long" in self.name:
            acc_splits_by_ass_class = {}
            for mode in intermodals:
                if mode == "train":
                    acc_splits_by_ass_class[intermodals[mode]] = access_splits[mode]["car"] * self.prob[mode]
                    acc_splits_by_ass_class[intermodals[mode].replace("mile","taxi")] = access_splits[mode]["car_pax"] * self.prob[mode]
                    acc_splits_by_ass_class[intermodals[mode].replace("first","last")] = access_splits[mode]["car"] * self.prob[mode]
                    acc_splits_by_ass_class[intermodals[mode].replace("first","last").replace("mile","taxi")] = access_splits[mode]["car_pax"] * self.prob[mode]
                elif mode == "airplane":
                    acc_splits_by_ass_class[intermodals[mode]] = access_splits[mode]["car"] + access_splits[mode]["car_pax"] * self.prob[mode]
                    acc_splits_by_ass_class[intermodals[mode].replace("first","last")] = (access_splits[mode]["car"] + access_splits[mode]["car_pax"])  * self.prob[mode]
                else:
                    acc_splits_by_ass_class[intermodals[mode]] = access_splits[mode]["car_pax"]  * self.prob[mode]
                    acc_splits_by_ass_class[intermodals[mode].replace("first","last")] = access_splits[mode]["car_pax"]  * self.prob[mode]
                acc_splits_by_ass_class[mode] = access_splits[mode]["transit"]  * self.prob[mode]
            self.prob.update(acc_splits_by_ass_class)
    
    def split_connection_mode(self, impedance, pt_mode, fm_mode, utility):
        expsum = numpy.zeros_like(utility)
        exps = {}
        fm_utils = {}
        access_split = {}
        access_modes = ("car_pax", "transit") if pt_mode == "long_d_bus" else ("car", "car_pax", "transit")
        for mode in access_modes:
            utility = numpy.zeros_like(expsum)
            parameters = self.get_acc_model_parameters(mode, pt_mode)
            utility = self._add_impedance(utility, parameters["b"], impedance, mode, pt_mode, fm_mode, parameters["avg_time_param_access"], parameters["acc_fac"])
            self._add_constant(utility, parameters["b"], mode, pt_mode)
            utility = self._add_zone_util(utility.T, parameters["b"], parameters["avg_time_param_access"], generation=True).T
            fm_utils[mode] = utility
            utility = utility*0.75 # Utility is scaled down (up) to get more (less) influence from unobserved variables
            exps[mode] = numpy.exp(utility)
            exps[mode][numpy.isnan(exps[mode])] = 1e-30
            exps[mode][(exps[mode])==0] = 1e-30
            expsum = expsum + exps[mode]
        
        logsum_path = Path(__file__).parent.parent / "models" / "logsum.omx"
        try:
            logsum_file = omx.open_file(logsum_path,"a")
        except:
            logsum_file = omx.open_file(logsum_path,"w")
        try:
            logsum_file[self.name[3:-5] + "_" + pt_mode][:] = numpy.log(expsum)
        except:
            logsum_file[self.name[3:-5] + "_" + pt_mode] = numpy.log(expsum)
        logsum_file.close()
        for a_mode in access_modes:
            access_split[a_mode] = (exps[a_mode]/expsum).T

        return access_split
    
    def _add_constant(self, utility, b, mode, pt_mode):
        const = 0
        if mode == "car":
            if pt_mode == "airplane":
                const = -1.3
            if pt_mode == "train":
                const = -5.875
        if mode == "car_pax":
            if pt_mode == "airplane":
                const = -1.95
            if pt_mode == "train":
                const = -4.85
            if pt_mode == "long_d_bus":
                const = -6
        try: # If only one parameter
            utility += const
        except ValueError: # Separate sub-region parameters
            for i, bounds in enumerate(self.sub_bounds):
                if utility.ndim == 1: # 1-d array calculation
                        utility[bounds] += const[i]
                else: # 2-d matrix calculation
                        utility[bounds, :] += const[i]
        return utility
    
    def _add_zone_util(self, utility, b, avg_time_param_access, generation=False):
        nest_param = b["mode_acc"]["log"]["logsum"]
        zdata = self.zone_data
        for i in b["mode_acc"]["generation"]:
            try: # If only one parameter
                utility += b["mode_acc"]["generation"][i] * zdata.get_data(i, self.bounds, generation) / nest_param
            except ValueError: # Separate sub-region parameters
                for j, bounds in enumerate(self.sub_bounds):
                    data = zdata.get_data(i, bounds, generation)
                    if utility.ndim == 1: # 1-d array calculation
                        utility[bounds] += data  * b["mode_acc"]["generation"][i] / nest_param
                    else: # 2-d matrix calculation
                        utility[bounds, :] += data  * b["mode_acc"]["generation"][i] / nest_param
        return utility
    def pnr_cost_by_purpose_duration(self, cost, perc_bcost, actual_bcost, fm_mode, remove_pnr_cost=0):
        pnr_duration = {"j_first_mile": {"avg": 2.18, "business": 1.12, "leisure": 2.64, "work": 1.41},
                        "e_first_mile": {"avg": 2.62, "business": 2.43, "leisure": 3.06, "work": 0.89},
                        "l_first_mile": {"avg": 2.39, "business": 2.01, "leisure": 2.51, "work": 1.12}}
        pnr_cost_24h = (perc_bcost-actual_bcost*vot_inv[vot_classes[fm_mode]])/(vot_inv[vot_classes[fm_mode]]*(pnr_duration[fm_mode]["avg"]-2))
        cost -= pnr_cost_24h*2
        if not remove_pnr_cost:
            cost += pnr_cost_24h*pnr_duration[fm_mode][self.name[3:-5]]
        return cost

    def _add_impedance(self, utility, b, impedance, acc_mode, pt_mode, fm_mode, avg_time_param_access, acc_fac):
        mode = pt_mode if acc_mode == "transit" else fm_mode
        if acc_mode == "car_pax" and mode == "j_first_mile":
            mode = "j_first_taxi"
        if acc_mode == "car":
            impedance[mode]["cost"] = self.pnr_cost_by_purpose_duration(impedance[mode]["cost"], impedance[mode]["perc_bcost"], impedance[mode]["board_cost"], mode, 0)
        if acc_mode == "car_pax" and fm_mode == "l_first_mile":
            impedance[mode]["cost"] = self.pnr_cost_by_purpose_duration(impedance[mode]["cost"], impedance[mode]["perc_bcost"], impedance[mode]["board_cost"], mode, 1)
        b_t_main = avg_time_param_access / acc_fac
        if self.name == "hb_leisure_long":
            b_c_main = -0.06857 # Cost param from short-trips model parameters
        else:
            b_c_main = -0.06237 # Cost param from short-trips model parameters
        b_t_transit = b["dest_transit_acc"]["impedance"]["time"] 
        b_t_acc = b["dest_acc"]["impedance"]["time"] 

        utility += b_t_main*(impedance[mode]["total_time"] - impedance[mode]["loc_time"] - impedance[mode]["aux_time"])
        aux_time = aux_transit_time["perception_factor"]*(impedance[mode]["aux_time"]-impedance[mode]["car_time"]) if acc_mode != "transit" else aux_transit_time["perception_factor"]*impedance[mode]["aux_time"]
        utility += b_c_main * impedance[mode]["cost"]
        if acc_mode == "car":
            utility += b_c_main * 0.12 * impedance[mode]["car_dist"]
            utility += b_t_acc * impedance[mode]["car_time"] / 3 # Car time was given a speed factor of one over three in assignment
        if acc_mode == "car_pax":
            utility += b_t_acc * impedance[mode]["car_time"] / 3
        utility += b_t_transit * (impedance[mode]["loc_time"] + aux_time)
        
        return utility
            
    def get_acc_model_parameters(self, acc_mode, pt_mode):
        # This function gets parameters for the connection mode choice model. Currently derives from short-trips model parameters, 
        # but also direct numericals (there multiplied by utility scale factor 0.75) are reported in the related master's thesis and could be used.
        parameters_path = Path(__file__).parent.parent / "parameters" / "demand"
        for file in parameters_path.rglob("hb_leisure.json"):
            param_short = json.loads(file.read_text("utf-8"))
        for file in parameters_path.rglob(self.name + ".json"):
            param_mainmode = json.loads(file.read_text("utf-8"))
        b_mode_acc: Optional[Dict[str, Dict[str, Any]]] = param_short["mode_choice"][acc_mode + ("_leisure" if acc_mode != "car_pax" else "")]
        b_dest_acc: Dict[str, Dict[str, Any]] = param_short["destination_choice"][acc_mode + ("_leisure" if acc_mode != "car_pax" else "")]
        b_dest_transit_acc: Dict[str, Dict[str, Any]] = param_short["destination_choice"]["transit_leisure"]
        b_dest_main: Dict[str, Dict[str, Any]] = param_mainmode["destination_choice"][pt_mode]
        b = {"mode_acc": b_mode_acc, "dest_acc":  b_dest_acc, "dest_main": b_dest_main, "dest_transit_acc": b_dest_transit_acc}
        avg_time_param_access = 0
        # Get weighted average (WA) of time parameter from short trips model, where weight = mode share
        weight = {"train": {"hb_business_long": {"car": 0.16, "car_pax": 0.11, "transit": 0.73}, "hb_leisure_long": {"car": 0, "car_pax": 0.32, "transit": 0.67}, "hb_work_long": {"car": 0.11, "car_pax": 0, "transit": 0.89}},
                  "long_d_bus": {"hb_business_long": {"car": 0, "car_pax": 0, "transit": 1}, "hb_leisure_long": {"car": 0.01, "car_pax": 0.24, "transit": 0.67}, "hb_work_long": {"car": 0.09, "car_pax": 0, "transit": 0.91}},
                  "airplane": {"hb_business_long": {"car": 0.23, "car_pax": 0.57, "transit": 0.20}, "hb_leisure_long": {"car": 0.23, "car_pax": 0.57, "transit": 0.20}, "hb_work_long": {"car": 0.23, "car_pax": 0.57, "transit": 0.20}}}
        for mode in ["car", "car_pax", "transit"]:
            avg_time_param_access += weight[pt_mode][self.name][mode]*param_short["destination_choice"][mode + ("_leisure" if mode != "car_pax" else "")]["impedance"]["time"]
        # Access time factor is the multiplier for access travel time in relation to main mode time. Thus, main mode time = WA/acc_fac.
        acc_fac = 1.36
        return {"b": b, "avg_time_param_access": avg_time_param_access, "acc_fac": acc_fac}

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
        for mode in ["j_first_mile", "j_first_taxi", "e_first_mile", "l_first_mile","j_last_mile", "j_last_taxi", "e_last_mile", "l_last_mile"]:
            mtx = (self.prob.pop(mode) * tours).T
            try:
               self.sec_dest_purpose.gen_model.add_tours(mtx, mode, self)
            except AttributeError:
               pass
            demand[mode] = Demand(self, mode, mtx)
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
