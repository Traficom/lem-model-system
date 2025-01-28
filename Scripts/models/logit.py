from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast
import numpy # type: ignore
import pandas
import copy
from collections import defaultdict

if TYPE_CHECKING:
    from datahandling.resultdata import ResultsData
    from datahandling.zonedata import ZoneData
    from datatypes.purpose import TourPurpose

import utils.log


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
        self.mode_utils: Dict[str, numpy.array] = {}
        self.dest_choice_param: Dict[str, Dict[str, Any]] = parameters["destination_choice"]
        self.mode_choice_param: Optional[Dict[str, Dict[str, Any]]] = parameters["mode_choice"]
        self.distance_boundary = parameters["distance_boundaries"]

    def _calc_mode_util(self, mode: str, impedance: Dict[str, numpy.ndarray]):
        b = self.mode_choice_param[mode]
        utility = numpy.zeros_like(next(iter(impedance.values())))
        self._add_constant(utility, b["constant"])
        utility = self._add_zone_util(
            utility.T, b["generation"], generation=True).T
        self._add_zone_util(utility, b["attraction"])
        self._add_impedance(utility, impedance, b["impedance"])
        self._add_log_impedance(utility, impedance, b["log"])
        self.mode_utils[mode] = utility
        exps = numpy.exp(utility)
        dist = self.purpose.dist
        if dist.shape == exps.shape:
            # If this is the lower level in nested model
            l, u = self.distance_boundary[mode]
            exps[(dist < l) | (dist >= u)] = 0
        return exps

    def _calc_mode_utils(self, impedance: Dict[str, Dict[str, numpy.ndarray]]):
        mode_exps: Dict[str, numpy.ndarray] = {}
        for mode in self.mode_choice_param:
            mode_exps[mode] = self._calc_mode_util(mode, impedance[mode])
        expsum: numpy.ndarray = sum(mode_exps.values())
        return expsum, mode_exps

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

        If model for non-home-based tours has individual dummy variables
        representing parent tour mode choice, None will be returned,
        because it requires parent tour demand to be calculated first.
        In this case, `calc_prob_again` will be called later.

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
        mode_exps, mode_expsum, dest_exps, dest_expsums = self._calc_utils(
            impedance)
        mode_probs = self._calc_mode_prob(mode_exps, mode_expsum)
        ec_mode = "car_electric"
        if mode_probs is None:
            self._stashed_exps += [dest_exps, dest_expsums, impedance[ec_mode]]
            return None
        if ec_mode in impedance:
            mode_probs, dest_exps[ec_mode], dest_expsums[ec_mode] = self._calc_electric_car_prob(
                impedance.pop(ec_mode), mode_exps, mode_probs)
        return self._calc_prob(mode_probs, dest_exps, dest_expsums)

    def _calc_electric_car_prob(self, impedance, mode_exps, mode_probs):
        ec_mode = "car_electric"
        dest_exps = self._calc_dest_util(
            self.purpose.car_mode, impedance)
        try:
            expsum = dest_exps.sum(1)
        except ValueError:
            expsum = dest_exps.sum()
        dest_expsum = {"logsum": expsum}
        mode_exps[self.purpose.car_mode] = self._calc_mode_util(
            self.purpose.car_mode, dest_expsum)
        ec_mode_probs = self._calc_mode_prob(
            mode_exps, sum(mode_exps.values()))
        ec_share = self.zone_data.get_data(
            "share_electric_cars", self.bounds, generation=True)
        for mode in self.mode_choice_param:
            if mode == self.purpose.car_mode:
                mode_probs[mode] = (1-ec_share) * mode_probs[mode]
                mode_probs[ec_mode] = ec_share * ec_mode_probs[mode]
            else:
                mode_probs[mode] = ((1-ec_share) * mode_probs[mode]
                                    + ec_share * ec_mode_probs[mode])
        return mode_probs, dest_exps, dest_expsum

    def calc_prob_again(self) -> dict:
        """Return matrix of choice probabilities.

        First recovers basic probabilities. Then inserts individual
        dummy variables by calling `calc_individual_prob()`.

        Returns
        -------
        dict
            Mode (car/transit/bike/walk) : numpy 2-d matrix
                Choice probabilities
        """
        mode_exps, mode_expsum, dest_exps, dest_expsums, impedance = self._stashed_exps
        del self._stashed_exps
        mode_probs = self._calc_mode_prob(mode_exps, mode_expsum)
        ec_mode = "car_electric"
        mode_probs, dest_exps[ec_mode], dest_expsums[ec_mode] = self._calc_electric_car_prob(
            impedance, mode_exps, mode_probs)
        return self._calc_prob(mode_probs, dest_exps, dest_expsums)

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
        _, _, dest_exps, _ = self._calc_utils(impedance)
        self.cumul_dest_prob = {}
        for mode in self.mode_choice_param:
            cumsum = dest_exps.pop(mode).T.cumsum(axis=0)
            self.cumul_dest_prob[mode] = cumsum / cumsum[-1]
    
    def _calc_individual_prob(self, mod_mode: str, dummy: str,
                              mode_exps: Dict[str, numpy.ndarray]):
        """Calculate utilities with individual dummies included.

        Parameters
        ----------
        mod_mode : str
            The mode for which the utility will be modified
        dummy : str
            The name of the individual dummy
        mode_exps : dict
            key : str
                Mode
            value : numpy.ndarray
                Utility exponentials to modify
        Returns
        -------
        dict
            key : str
                Mode
            value : numpy.ndarray
                Modified utility exponentials
        """
        b = self.mode_choice_param[mod_mode]["individual_dummy"][dummy]
        mode_exps2 = copy.deepcopy(mode_exps)
        try:
            mode_exps2[mod_mode] *= numpy.exp(b)
        except ValueError:
            for i, bounds in enumerate(self.sub_bounds):
                mode_exps2[mod_mode][bounds] *= numpy.exp(b[i])
        return mode_exps2
    
    def calc_individual_mode_prob(self, zone: int,
                                  individual_dummy: Optional[str] = None,
                                  ) -> Tuple[numpy.ndarray, float]:
        """Calculate individual choice probabilities with individual dummies.
        
        Calculate mode choice probabilities for individual
        agent with individual dummy variable included.

        Additionally save and rescale logsum values for agent based accessibility 
        analysis.
        
        Parameters
        ----------
        zone : int
            Index of zone where the agent lives
        individual_dummy : str (optional)
            Name of individual dummy to take into account in utility
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
            if individual_dummy in b:
                try:
                    mode_utils[i] += b[individual_dummy]
                except ValueError:
                    # Separate sub-region parameters
                    j = self.purpose.sub_intervals.searchsorted(
                        zone, side="right")
                    mode_utils[i] += b[individual_dummy][j]
        return mode_utils

    def _calc_utils(self,
                    impedance: Dict[str, Dict[str, Dict[str, numpy.ndarray]]]):
        dest_expsums: Dict[str, numpy.ndarray] = {}
        dest_exps: Dict[str, numpy.ndarray] = {}
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
        mode_expsum, mode_exps = self._calc_mode_utils(dest_expsums)
        logsum = pandas.Series(
            log(mode_expsum), self.purpose.zone_numbers,
            name=self.purpose.name)
        self.zone_data._values[self.purpose.name] = logsum
        return mode_exps, mode_expsum, dest_exps, dest_expsums

    def _calc_mode_prob(self, mode_exps: Dict[str, numpy.ndarray],
                        mode_expsum: numpy.ndarray,
                        ) -> Dict[str, numpy.ndarray]:
        mode_probs = defaultdict(list)
        no_dummy_share = 1.0
        for mode in self.mode_choice_param:
            for i in self.mode_choice_param[mode]["individual_dummy"]:
                try:
                    dummy_share = self.zone_data.get_data(
                        i, self.bounds, generation=True)
                except KeyError:
                    self._stashed_exps = [mode_exps, mode_expsum]
                    return None
                no_dummy_share -= dummy_share
                mode_exps2 = self._calc_individual_prob(mode, i, mode_exps)
                mode_expsum2 = sum(mode_exps2.values())
                for mode2 in mode_exps2:
                    mode_probs[mode2].append(
                        dummy_share * divide(mode_exps2[mode2], mode_expsum2))
            mode_probs[mode].append(
                no_dummy_share * divide(mode_exps[mode], mode_expsum))
        return mode_probs

    def _calc_prob(self, mode_probs: Dict[str, numpy.ndarray],
                   dest_exps: Dict[str, numpy.ndarray],
                   dest_expsums: Dict[str, numpy.ndarray]
                   ) -> Dict[str, numpy.ndarray]:
        prob = {}
        for mode in mode_probs:
            dest_exp = dest_exps.pop(mode).T
            dest_expsum = dest_expsums[mode]["logsum"]
            dest_prob = divide(dest_exp, dest_expsum)
            prob[mode] = sum(mode_probs[mode]) * dest_prob
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
        mode_exps, mode_expsum, _, _ = self._calc_utils(impedance)
        self.accessibility = {}
        self.accessibility["all"] = self.zone_data[self.purpose.name]
        sustainable_expsum = numpy.zeros_like(mode_expsum)
        car_expsum = numpy.zeros_like(mode_expsum)
        for mode in self.mode_choice_param:
            logsum = self.zone_data[f"{self.purpose.name}_{mode}"]
            self.accessibility[mode] = logsum
            if "car" in mode:
                car_expsum += mode_exps[mode]
            else:
                sustainable_expsum += mode_exps[mode]
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
        prob = self._calc_prob(impedance)

        # Calculate electric car probability and add to prob
        ec_mode = "car_electric"
        if ec_mode in impedance:
            impedance[self.purpose.car_mode] = impedance[ec_mode]
            ec_prob = self._calc_prob(impedance)
            ec_share = self.zone_data.get_data(
                "share_electric_cars", self.bounds, generation=True)
            for mode in self.mode_choice_param:
                if mode == self.purpose.car_mode:
                    prob[mode] = (1-ec_share) * prob[mode]
                    prob[ec_mode] = ec_share * ec_prob[mode]
                else:
                    prob[mode] = ((1-ec_share) * prob[mode]
                                + ec_share * ec_prob[mode])

        return prob

    def _calc_prob(self, impedance):
        mode_expsum, mode_exps = self._calc_mode_utils(impedance)
        self.mode_utils = {}
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
        for mode in self.mode_choice_param:
            mode_prob = divide(mode_exps.pop(mode), mode_expsum).T
            prob[mode] = mode_prob * dest_prob
        return prob

    def calc_basic_prob(self, impedance):
        mode_expsum, _ = self._calc_mode_utils(impedance)
        dest_exps = self._calc_dest_util("logsum", {"logsum": mode_expsum})
        cumsum = dest_exps.T.cumsum(axis=0)
        self.cumul_dest_prob = cumsum / cumsum[-1]

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
