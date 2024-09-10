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
from parameters.assignment import assignment_classes
import parameters.cost as cost
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
                    msg = (f"Purpose {self.name}: " 
                           + f"Added {round(100*(p-1))} % to {t} : {m}.")
                    log.warn(msg)
                except KeyError:
                    pass
        # Apply discounts and transformations to LOS matrices
        for mode in day_imp:
            for mtx_type in day_imp[mode]:
                if mtx_type == "cost":
                    try:
                        day_imp[mode][mtx_type] *= cost.cost_discount[self.name][mode]
                    except KeyError:
                        pass
                if mtx_type == "time" and "car" in mode:
                    day_imp[mode][mtx_type] += self.zone_data["park_time"].values
                if mtx_type == "cost" and "car" in mode:
                    try:
                        day_imp[mode][mtx_type] += (cost.activity_time[self.name] *
                                                    cost.share_paying[self.name] *
                                                    self.zone_data["park_cost"].values)
                    except KeyError:
                        pass
                if mtx_type == "cost" and mode in ["car_work", "car_leisure"]:
                    try:
                        day_imp[mode][mtx_type] *= (1 - cost.sharing_factor[self.name] *
                                                    (cost.car_drv_occupancy[self.name] - 1) /
                                                    cost.car_drv_occupancy[self.name])
                    except KeyError:
                        pass
                if mtx_type == "cost" and mode == "car_pax":
                    try:
                        day_imp[mode][mtx_type] *= (cost.sharing_factor[self.name] /
                                                    cost.car_drv_occupancy[self.name])
                    except KeyError:
                        pass
        log.info(f"Matrix transformations completed for {self.name}")
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
    attempt_calibration(specification)
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
        self.mappings = self.zone_data.aggregations.mappings
        self.aggregates = {name: {} for name in self.mappings}
        self.within_zone_tours = {}
        self.sec_dest_purpose = None

    @property
    def dist(self):
        return self.distance[self.bounds, self.dest_interval]
    
    @property
    def generated_tours_all(self):
        return pandas.Series(
            sum(self.generated_tours.values()), self.zone_numbers)
    
    @property
    def attracted_tours_all(self):
        return pandas.Series(
            sum(self.generated_tours.values()), self.zone_numbers)
    
    @property
    def generation_mode_shares(self):
        shares = {mode: (self.generated_tours[mode].sum() 
                          / self.generated_tours_all.sum()) for mode in self.modes}
        return pandas.concat({self.name: pandas.Series(shares, name="mode_share")}, 
                             names=["purpose", "mode"])
    
    @property
    def tour_lengths(self):
        lengths = {mode: self.histograms[mode].histogram for mode in self.histograms}
        return pandas.concat(lengths, names=["mode", "purpose", "interval"])

    def init_sums(self):
        for name in self.aggregates:
            agg = self.mappings[name].drop_duplicates()
            for mode in self.modes:
                self.aggregates[name][mode] = pandas.DataFrame(0, agg, agg)
        for mode in self.modes:
            self.generated_tours[mode] = numpy.zeros_like(self.zone_numbers)
            self.attracted_tours[mode] = numpy.zeros_like(self.zone_data.zone_numbers)
            self.histograms[mode].__init__(self.name)
            self.within_zone_tours[mode] = pandas.Series(
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
            for mapping in self.aggregates:
                self.aggregates[mapping][mode] = agg.aggregate_mtx(
                    pandas.DataFrame(
                        mtx, self.zone_numbers, self.zone_data.zone_numbers),
                    mapping)
            self.within_zone_tours[mode] = pandas.Series(
                numpy.diag(mtx), self.zone_numbers,
                name="{}_{}".format(self.name, mode))
        log.info(f"Demand calculated for {self.name}")
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

def attempt_calibration(spec: dict):
    """Check if specification includes "calibration" trees.

    Transform regular parameters to include calibration,
    remove separate calibration parameters.
    A calibration (named "calibration") tree can be anywhere in the dict,
    but must refer to existing adjacent parameters or trees of parameters.
    """
    try:
        param_names = list(spec.keys())
    except AttributeError:
        # No calibration parameters in this branch, return up
        return
    for param_name in param_names:
        if param_name == "calibration":
            calibrate(spec, spec.pop(param_name))
        else:
            # Search deeper
            attempt_calibration(spec[param_name])

def calibrate(spec: dict, calib_spec: dict):
    for param_name in calib_spec:
        try:
            spec[param_name] += calib_spec[param_name]
        except TypeError:
            # Search deeper
            calibrate(spec[param_name], calib_spec[param_name])
