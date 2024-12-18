from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast
import numpy # type: ignore
import pandas
import math
if TYPE_CHECKING:
    from datahandling.resultdata import ResultsData
    from datahandling.zonedata import ZoneData
    from datatypes.purpose import TourPurpose

import parameters.zone as param


def log(a: numpy.array):
    with numpy.errstate(divide="ignore"):
        return numpy.log(a)

def divide(a, b):
    return numpy.divide(a, b, out=numpy.zeros_like(a), where=b!=0)

class LogitModel:
    """Generic logit model with mode/destination choice.

    Parameters
    ----------
    purpose : TourPurpose
        Tour purpose (type of tour)
    parameters : dict
        See `datatypes.purpose.new_tour_purpose()`
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object to result directory
    """

    def __init__(self, 
                 purpose: TourPurpose,
                 parameters: dict,
                 zone_data: ZoneData,
                 resultdata: ResultsData):
        self.resultdata = resultdata
        self.purpose = purpose
        self.bounds = purpose.bounds
        self.sub_bounds = purpose.sub_bounds
        self.zone_data = zone_data
        self.mode_exps: Dict[str, numpy.array] = {}
        self.mode_utils: Dict[str, numpy.array] = {}
        self.dest_choice_param: Dict[str, Dict[str, Any]] = parameters["destination_choice"]
        self.mode_choice_param: Optional[Dict[str, Dict[str, Any]]] = parameters["mode_choice"]
        self.distance_boundary = parameters["distance_boundaries"]

    def _calc_mode_util(self, impedance):
        expsum = numpy.zeros_like(
            next(iter(next(iter(impedance.values())).values())))
        for mode in self.mode_choice_param:
            b = self.mode_choice_param[mode]
            utility = numpy.zeros_like(expsum)
            self._add_constant(utility, b["constant"])
            utility = self._add_zone_util(
                utility.T, b["generation"], generation=True).T
            self._add_zone_util(utility, b["attraction"])
            self._add_impedance(utility, impedance[mode], b["impedance"])
            self._add_log_impedance(utility, impedance[mode], b["log"])
            self.mode_utils[mode] = utility
            exps = numpy.exp(utility)
            dist = self.purpose.dist
            if dist.shape == exps.shape:
                # If this is the lower level in nested model
                l, u = self.distance_boundary[mode]
                exps[(dist < l) | (dist >= u)] = 0
            self.mode_exps[mode] = exps
            expsum += exps
        return expsum
    
    def _calc_dest_util(self, mode: str, impedance: dict) -> numpy.ndarray:
        b = self.dest_choice_param[mode]
        utility: numpy.array = numpy.zeros_like(next(iter(impedance.values())))
        self._add_zone_util(utility, b["attraction"])
        self._add_impedance(utility, impedance, b["impedance"])
        size = numpy.zeros_like(utility)
        self._add_zone_util(size, b["attraction_size"])
        impedance["attraction_size"] = size
        if "transform" in b:
            b_transf = b["transform"]
            transimp = numpy.zeros_like(utility)
            self._add_zone_util(transimp, b_transf["attraction"])
            self._add_impedance(transimp, impedance, b_transf["impedance"])
            impedance["transform"] = transimp
        self._add_log_impedance(utility, impedance, b["log"])
        dest_exp = numpy.exp(utility)
        if mode != "logsum":
            l, u = self.distance_boundary[mode]
            dist = self.purpose.dist
            dest_exp[(dist < l) | (dist >= u)] = 0
        if mode == "airplane":
            dest_exp[impedance["cost"] < 80] = 0
        return dest_exp
    
    def _calc_sec_dest_util(self, mode, impedance, orig, dest):
        b = self.dest_choice_param[mode]
        utility = numpy.zeros_like(next(iter(impedance.values())))
        self._add_sec_zone_util(utility, b["attraction"], orig, dest)
        self._add_impedance(utility, impedance, b["impedance"])
        dest_exps = numpy.exp(utility)
        size = numpy.zeros_like(utility)
        self._add_sec_zone_util(size, b["attraction_size"])
        impedance["attraction_size"] = size
        self._add_log_impedance(dest_exps, impedance, b["log"])
        if mode != "logsum":
            l, u = self.distance_boundary[mode]
            dest_exps[(impedance["dist"] < l) | (impedance["dist"] >= u)] = 0
        return dest_exps

    def _add_constant(self, utility, b):
        """Add constant term to utility.

        If parameter b is a tuple of two terms, they will be added for
        capital region and surrounding region respectively.
        
        Parameters
        ----------
        utility : ndarray
            Numpy array to which the constant b will be added
        b : float or tuple
            The value of the constant
        """
        try: # If only one parameter
            utility += b
        except ValueError: # Separate sub-region parameters
            for i, bounds in enumerate(self.sub_bounds):
                if utility.ndim == 1: # 1-d array calculation
                    utility[bounds] += b[i]
                else: # 2-d matrix calculation
                    utility[bounds, :] += b[i]
    
    def _add_impedance(self, utility, impedance, b):
        """Adds simple linear impedances to utility.

        If parameter in b is tuple of two terms, they will be added for
        capital region and surrounding region respectively.
        
        Parameters
        ----------
        utility : ndarray
            Numpy array to which the impedances will be added
        impedance : dict
            A dictionary of time-averaged impedance matrices. Includes keys
            `time`, `cost`, and `dist` of which values are all ndarrays.
        b : dict
            The parameters for different impedance matrices.
        """
        for i in b:
            try: # If only one parameter
                utility += b[i] * impedance[i]
            except ValueError: # Separate sub-region parameters
                for j, bounds in enumerate(self.sub_bounds):
                    utility[bounds, :] += b[i][j] * impedance[i][bounds, :]
        return utility

    def _add_log_impedance(self, utility, impedance, b):
        """Adds log transformations of impedance to utility.

        If parameter in b is tuple of two terms, they will be multiplied for
        capital region and surrounding region respectively.

        Parameters
        ----------
        exps : ndarray
            Numpy array to which the impedances will be multiplied
        impedance : dict
            A dictionary of time-averaged impedance matrices. Includes keys
            `time`, `cost`, and `dist` of which values are all ndarrays.
        b : dict
            The parameters for different impedance matrices
        """
        for i in b:
            try: # If only one parameter
                imp = impedance[i] + 1 if b[i] < 0 else impedance[i]
                utility += b[i] * log(imp)
            except ValueError: # Separate sub-region parameters
                for j, bounds in enumerate(self.sub_bounds):
                    imp = impedance[i][bounds, :]
                    if b[i][j] < 0:
                        imp += 1
                    utility[bounds, :] += b[i][j] * log(imp)
        return utility

    def _add_zone_util(self, utility, b, generation=False):
        """Adds simple linear zone terms to utility.

        If parameter in b is tuple of two terms, they will be added for
        capital region and surrounding region respectively.
        
        Parameters
        ----------
        utility : ndarray
            Numpy array to which the impedances will be added
        b : dict
            The parameters for different zone data.
        generation : bool
            Whether the effect of the zone term is added only to the
            geographical area in which this model is used based on the
            `self.bounds` attribute of this class.
        """
        zdata = self.zone_data
        for i in b:
            try: # If only one parameter
                utility += b[i] * zdata.get_data(i, self.bounds, generation)
            except ValueError: # Separate sub-region parameters
                for j, bounds in enumerate(self.sub_bounds):
                    data = zdata.get_data(i, bounds, generation)
                    if utility.ndim == 1: # 1-d array calculation
                        utility[bounds] += b[i][j] * data
                    else: # 2-d matrix calculation
                        utility[bounds, :] += b[i][j] * data
        return utility
    
    def _add_sec_zone_util(self, utility, b, orig=None, dest=None):
        for i in b:
            data = self.zone_data.get_data(i, self.bounds, generation=True)
            try: # If only one parameter
                utility += b[i] * data
            except ValueError: # Separate params for orig and dest
                utility += b[i][0] * data[orig, self.bounds]
                utility += b[i][1] * data[dest, self.bounds]
        return utility

    def _add_log_zone_util(self, exps, b, generation=False):
        """Adds log transformations of zone data to utility.
        
        This is an optimized way of calculating log terms. Calculates
        zonedata1^b1 * ... * zonedataN^bN in the following equation:
        e^(linear_terms + b1*log(zonedata1) + ... + bN*log(zonedataN))
        = e^(linear_terms) * zonedata1^b1 * ... * zonedataN^bN

        If parameter in b is tuple of two terms, they will be multiplied for
        capital region and surrounding region respectively.

        Parameters
        ----------
        utility : ndarray
            Numpy array to which the impedances will be added
        b : dict
            The parameters for different zone data.
        generation : bool
            Whether the effect of the zone term is added only to the
            geographical area in which this model is used based on the
            `self.bounds` attribute of this class.
        """
        zdata = self.zone_data
        for i in b:
            exps *= numpy.power(
                zdata.get_data(i, self.bounds, generation) + 1, b[i])
        return exps


class ModeDestModel(LogitModel):
    """Nested logit model with mode choice in upper level.

    Uses logsums from destination choice model as utility
    in mode choice model.

         choice
        /     \\
      m1        m2
     / \\      / \\
    d1   d2   d1   d2

    Parameters
    ----------
    purpose : TourPurpose
        Tour purpose (type of tour)
    parameters : dict
        See `datatypes.purpose.new_tour_purpose()`
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object to result directory
    """
    def __init__(self, *args, **kwargs):
        LogitModel.__init__(self, *args, **kwargs)
        try:
            b = self.dest_choice_param["car"]["impedance"]["cost"]
        except KeyError:
            # School tours do not have a constant cost parameter
            # Use value of time conversion from CBA guidelines instead
            b = -0.46738697
        try:
            # Convert utility into euros
            money_utility = 1 / b
        except TypeError:
            # Separate sub-region parameters
            money_utility = 1 / b[0]
        money_utility /= next(iter(self.mode_choice_param.values()))["log"]["logsum"]
        self.money_utility = money_utility

    def calc_prob(self, impedance: dict) -> dict:
        """Calculate matrix of choice probabilities.

        First calculates basic probabilities. Then inserts individual
        dummy variables by calling `calc_individual_prob()`.
        
        Parameters
        ----------
        impedance : dict
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2-d matrix
                    Impedances
        
        Returns
        -------
        dict
            Mode (car/transit/bike/walk) : numpy 2-d matrix
                Choice probabilities
        """
        prob = self._calc_prob(*self._calc_utils(impedance))
        for mod_mode in self.mode_choice_param:
            for i in self.mode_choice_param[mod_mode]["individual_dummy"]:
                dummy_share = self.zone_data.get_data(
                    i, self.bounds, generation=True)
                ind_prob = self.calc_individual_prob(mod_mode, i)
                for mode in prob:
                    no_dummy = (1 - dummy_share) * prob[mode]
                    dummy = dummy_share * ind_prob[mode]
                    prob[mode] = no_dummy + dummy
        return prob
    
    def calc_basic_prob(self, impedance: dict):
        """Calculate utilities and cumulative destination choice probabilities.

        Only used in agent simulation.
        Individual dummy variables are not included.
        
        Parameters
        ----------
        impedance : dict
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2-d matrix
                    Impedances
        """
        _, dest_exps, _ = self._calc_utils(impedance)
        self.cumul_dest_prob = {}
        for mode in self.mode_choice_param:
            cumsum = dest_exps.pop(mode).T.cumsum(axis=0)
            self.cumul_dest_prob[mode] = cumsum / cumsum[-1]
    
    def calc_individual_prob(self, mod_mode: str, dummy: str) -> dict:
        """Calculate matrix of probabilities with individual dummies.
        
        Calculate matrix of mode and destination choice probabilities
        with individual dummy variable included.
        
        Parameters
        ----------
        mod_mode : str
            The mode for which the utility will be modified
        dummy : str
            The name of the individual dummy
        
        Returns
        -------
        dict
            Mode (car/transit/bike/walk) : numpy 2-d matrix
                Choice probabilities
        """
        b = self.mode_choice_param[mod_mode]["individual_dummy"][dummy]
        try:
            self.mode_exps[mod_mode] *= numpy.exp(b)
        except ValueError:
            for i, bounds in enumerate(self.sub_bounds):
                self.mode_exps[mod_mode][bounds] *= numpy.exp(b[i])
        mode_expsum = numpy.zeros_like(self.mode_exps[mod_mode])
        for mode in self.mode_choice_param:
            mode_expsum += self.mode_exps[mode]
        return self._calc_prob(mode_expsum)
    
    def calc_individual_mode_prob(self, 
                                  is_car_user: bool, 
                                  zone: int) -> Tuple[numpy.ndarray, float]:
        """Calculate individual choice probabilities with individual dummies.
        
        Calculate mode choice probabilities for individual
        agent with individual dummy variable "car_users" included.

        Additionally save and rescale logsum values for agent based accessibility 
        analysis.
        
        Parameters
        ----------
        is_car_user : bool
            Whether the agent is car user or not
        zone : int
            Index of zone where the agent lives
        
        Returns
        -------
        numpy.ndarray
            Choice probabilities for purpose modes
        float
            Total accessibility for individual (eur)
        """
        modes = self.purpose.modes
        mode_utils = numpy.empty(len(modes))
        for i, mode in enumerate(modes):
            mode_utils[i] = self.mode_utils[mode][zone]
            b = self.mode_choice_param[mode]["individual_dummy"]
            if is_car_user and "car_users" in b:
                try:
                    mode_utils[i] += b["car_users"]
                except ValueError:
                    # Separate sub-region parameters
                    j = self.purpose.sub_intervals.searchsorted(
                        zone, side="right")
                    mode_utils[i] += b["car_users"][j]
        return mode_utils

    def _calc_utils(self, impedance: dict) -> Tuple[numpy.ndarray, dict, dict]:
        dest_expsums = {}
        dest_exps = {}
        for mode in self.dest_choice_param:
            dest_exps[mode] = self._calc_dest_util(mode, impedance.pop(mode))
            try:
                expsum = dest_exps[mode].sum(1)
            except ValueError:
                expsum = dest_exps[mode].sum()
            dest_expsums[mode] = {"logsum": expsum}
            label = self.purpose.name + "_" + mode
            logsum = pandas.Series(
                log(expsum), self.purpose.zone_numbers, name=label)
            self.zone_data._values[label] = logsum
        mode_expsum = self._calc_mode_util(dest_expsums)
        logsum = pandas.Series(
            log(mode_expsum), self.purpose.zone_numbers,
            name=self.purpose.name)
        self.zone_data._values[self.purpose.name] = logsum
        return mode_expsum, dest_exps, dest_expsums

    def _calc_prob(self, mode_expsum: numpy.ndarray,
                   dest_exps: dict,
                   dest_expsums: dict) -> dict:
        prob = {}
        for mode in self.mode_choice_param:
            mode_exps = self.mode_exps[mode]
            mode_prob = divide(mode_exps, mode_expsum)
            dest_exp = dest_exps.pop(mode).T
            dest_expsum = dest_expsums[mode]["logsum"]
            dest_prob = divide(dest_exp, dest_expsum)
            prob[mode] = mode_prob * dest_prob
        return prob


class AccessibilityModel(ModeDestModel):
    def calc_accessibility(self, impedance):
        """Calculate logsum-based accessibility measures.

        Individual dummy variables are not included.

        Parameters
        ----------
        impedance : dict
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2-d matrix
                    Impedances
        """
        mode_expsum, _, _ = self._calc_utils(impedance)
        self.accessibility = {}
        self.accessibility["all"] = self.zone_data[self.purpose.name]
        sustainable_expsum = numpy.zeros_like(mode_expsum)
        car_expsum = numpy.zeros_like(mode_expsum)
        for mode in self.mode_choice_param:
            logsum = self.zone_data[f"{self.purpose.name}_{mode}"]
            self.accessibility[mode] = logsum
            if "car" in mode:
                car_expsum += self.mode_exps[mode]
            else:
                sustainable_expsum += self.mode_exps[mode]
        self.accessibility["sustainable"] = numpy.log(sustainable_expsum)
        self.accessibility["car"] = numpy.log(car_expsum)
        for key in ["all", "sustainable", "car"]:
            self.accessibility[f"{key}_scaled"] = (self.money_utility
                                                   * self.accessibility[key])

    def _add_constant(self, utility, b):
        """Add constant term to utility.

        If parameter b is a tuple of two terms,
        capital region will be picked.

        Parameters
        ----------
        utility : ndarray
            Numpy array to which the constant b will be added
        b : float or tuple
            The value of the constant
        """
        try: # If only one parameter
            utility += b
        except ValueError: # Separate params for cap region and surrounding
            utility += b[0]

    def _add_impedance(self, utility, impedance, b):
        """Adds simple linear impedances to utility.

        If parameter in b is tuple of two terms,
        capital region will be picked.

        Parameters
        ----------
        utility : ndarray
            Numpy array to which the impedances will be added
        impedance : dict
            A dictionary of time-averaged impedance matrices. Includes keys
            `time`, `cost`, and `dist` of which values are all ndarrays.
        b : dict
            The parameters for different impedance matrices.
        """
        for i in b:
            try: # If only one parameter
                utility += b[i] * impedance[i]
            except ValueError: # Separate params for cap region and surrounding
                utility += b[i][0] * impedance[i]
        return utility

    def _add_log_impedance(self, utility, impedance, b):
        """Adds log transformations of impedance to utility.

        If parameter in b is tuple of two terms,
        capital region will be picked.

        Parameters
        ----------
        utility : ndarray
            Numpy array to which the impedances will be added
        impedance : dict
            A dictionary of time-averaged impedance matrices. Includes keys
            `time`, `cost`, and `dist` of which values are all ndarrays.
        b : dict
            The parameters for different impedance matrices
        """
        for i in b:
            try: # If only one parameter
                utility += b[i] * log(impedance[i] + 1)
            except ValueError: # Separate params for cap region and surrounding
                utility += b[i][0] * log(impedance[i] + 1)
        return utility

    def _add_zone_util(self, utility, b, generation=False):
        """Adds simple linear zone terms to utility.

        If parameter in b is tuple of two terms,
        capital region will be picked.

        Parameters
        ----------
        utility : ndarray
            Numpy array to which the impedances will be added
        b : dict
            The parameters for different zone data.
        generation : bool
            Whether the effect of the zone term is added only to the
            geographical area in which this model is used based on the
            `self.bounds` attribute of this class.
        """
        zdata = self.zone_data
        for i in b:
            try: # If only one parameter
                # Remove area dummies from accessibility indicators
                data = zdata.get_data(i, self.bounds, generation)
                if data.dtype != bool:
                    utility += b[i] * data
            except ValueError: # Separate params for cap region and surrounding
                utility += b[i][0] * zdata.get_data(i, self.bounds, generation)
        return utility


class DestModeModel(LogitModel):
    """Nested logit model with destination choice in upper level.

    Used only in peripheral non-home source model.
    Uses logsums from mode choice model as utility
    in destination choice model.

         choice
        /     \\
      d1        d2
     / \\      / \\
    m1   m2   m1   m2

    Parameters
    ----------
    purpose : TourPurpose
        Tour purpose (type of tour)
    parameters : dict
        See `datatypes.purpose.new_tour_purpose()`
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object to result directory
    """

    def calc_prob(self, impedance):
        """Calculate matrix of choice probabilities.
        
        Parameters
        ----------
        impedance : dict
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2-d matrix
                    Impedances
        
        Returns
        -------
        dict
            Mode (car/transit/bike/walk) : numpy 2-d matrix
                Choice probabilities
        """
        mode_expsum = self._calc_mode_util(impedance)
        dest_exps = self._calc_dest_util("logsum", {"logsum": mode_expsum})
        try:
            dest_expsum = dest_exps.sum(1)
        except ValueError:
            dest_expsum = dest_exps.sum()
        logsum = pandas.Series(
            log(dest_expsum), self.purpose.zone_numbers,
            name=self.purpose.name)
        self.accessibility = {"all": logsum}
        self.zone_data._values[self.purpose.name] = logsum
        prob = {}
        dest_prob = divide(dest_exps.T, dest_expsum)
        for mode, mode_exps in self.mode_exps.items():
            mode_prob = divide(mode_exps, mode_expsum).T
            prob[mode] = mode_prob * dest_prob
        return prob

    def calc_accessibility(self, *args):
        """Placeholder for accessibility measuring"""
        pass

class SecDestModel(LogitModel):
    """Logit model for secondary destination choice.

    Attaches secondary destinations to tours with already calculated
    modes and destinations.

    Parameters
    ----------
    zone_data : ZoneData
        Data used for all demand calculations
    purpose : TourPurpose
        Tour purpose (type of tour)
    resultdata : ResultData
        Writer object to result directory
    is_agent_model : bool (optional)
        Whether the model is used for agent-based simulation
    """

    def calc_prob(self, mode, impedance, origin, destination=None):
        """Calculate matrix of choice probabilities.
        
        Parameters
        ----------
        mode : str
            Mode (car/transit/bike)
        impedance : dict
            Type (time/cost/dist) : numpy 2d matrix
                Impedances
        origin: int
            Origin zone index
        destination: int or ndarray (optional)
            Destination zone index or boolean array (if calculation for 
            all primary destinations is performed in parallel)
        
        Returns
        -------
        numpy 2-d matrix
                Choice probabilities
        """
        dest_exps = self._calc_sec_dest_util(mode, impedance, origin, destination)
        return dest_exps.T / dest_exps.sum(1)


class OriginModel(DestModeModel):
    pass
