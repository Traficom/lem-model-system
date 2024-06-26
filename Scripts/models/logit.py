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
        self._dest_exps: Dict[str, numpy.array] = {}
        self.mode_exps: Dict[str, numpy.array] = {}
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
            exps = numpy.exp(utility)
            self._add_log_impedance(exps, impedance[mode], b["log"])
            self.mode_exps[mode] = exps
            expsum += exps
        return expsum
    
    def _calc_dest_util(self, mode, impedance):
        b = self.dest_choice_param[mode]
        utility: numpy.array = numpy.zeros_like(next(iter(impedance.values())))
        self._add_zone_util(utility, b["attraction"])
        self._add_impedance(utility, impedance, b["impedance"])
        self._dest_exps[mode] = numpy.exp(utility)
        size = numpy.zeros_like(utility)
        self._add_zone_util(size, b["attraction_size"])
        impedance["attraction_size"] = size
        if "transform" in b:
            b_transf = b["transform"]
            transimp = numpy.zeros_like(utility)
            self._add_zone_util(transimp, b_transf["attraction"])
            self._add_impedance(transimp, impedance, b_transf["impedance"])
            impedance["transform"] = transimp
        self._add_log_impedance(self._dest_exps[mode], impedance, b["log"])
        if mode != "logsum":
            l, u = self.distance_boundary[mode]
            dist = self.purpose.dist
            self._dest_exps[mode][(dist < l) | (dist >= u)] = 0
        if mode == "airplane":
            self._dest_exps[mode][impedance["cost"] < 150] = 0
        try:
            return self._dest_exps[mode].sum(1)
        except ValueError:
            return self._dest_exps[mode].sum()
    
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

    def _add_log_impedance(self, exps, impedance, b):
        """Adds log transformations of impedance to utility.
        
        This is an optimized way of calculating log terms. Calculates
        impedance1^b1 * ... * impedanceN^bN in the following equation:
        e^(linear_terms + b1*log(impedance1) + ... + bN*log(impedanceN))
        = e^(linear_terms) * impedance1^b1 * ... * impedanceN^bN

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
                exps *= numpy.power(imp, b[i])
            except TypeError: # Separate sub-region parameters
                for j, bounds in enumerate(self.sub_bounds):
                    imp = impedance[i][bounds, :]
                    if b[i][j] < 0:
                        imp += 1
                    exps[bounds, :] *= numpy.power(imp, b[i][j])
        return exps

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
        exps : ndarray
            Numpy array to which the impedances will be multiplied
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

    def calc_prob(self, impedance):
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
        prob = self._calc_prob(self._calc_utils(impedance))
        for mod_mode in self.mode_choice_param:
            for i in self.mode_choice_param[mod_mode]["individual_dummy"]:
                dummy_share = self.zone_data.get_data(
                    i, self.bounds, generation=True)
                ind_prob = self.calc_individual_prob(mod_mode, i)
                for mode in prob:
                    no_dummy = (1 - dummy_share) * prob[mode]
                    dummy = dummy_share * ind_prob[mode]
                    prob[mode] = no_dummy + dummy
        self._dest_exps.clear()
        return prob
    
    def calc_basic_prob(self, impedance):
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
        self._calc_utils(impedance)
        self.cumul_dest_prob = {}
        for mode in self.mode_choice_param:
            cumsum = self._dest_exps.pop(mode).T.cumsum(axis=0)
            self.cumul_dest_prob[mode] = cumsum / cumsum[-1]
    
    def calc_individual_prob(self, mod_mode, dummy):
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
                                  zone: int) -> Tuple[numpy.array, float]:
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
        numpy.array
            Choice probabilities for purpose modes
        float
            Total accessibility for individual (eur)
        """
        mode_exps = {}
        mode_expsum = 0
        modes = self.purpose.modes
        for mode in modes:
            mode_exps[mode] = self.mode_exps[mode][zone]
            self.mode_choice_param = cast(Dict[str, Dict[str, Any]], self.mode_choice_param) #type checker help
            b = self.mode_choice_param[mode]["individual_dummy"]
            if is_car_user and "car_users" in b:
                try:
                    mode_exps[mode] *= math.exp(b["car_users"])
                except TypeError:
                    # Separate sub-region parameters
                    i = self.purpose.sub_intervals.searchsorted(
                        zone, side="right")
                    mode_exps[mode] *= math.exp(b["car_users"][i])
            mode_expsum += mode_exps[mode]
        probs = numpy.empty(len(modes))
        for i, mode in enumerate(modes):
            probs[i] = mode_exps[mode] / mode_expsum
        # utils to money
        logsum = numpy.log(mode_expsum)
        b = self._get_cost_util_coefficient()
        try:
            # Convert utility into euros
            money_utility = 1 / b
        except TypeError:
            # Separate sub-region parameters
            i = self.purpose.sub_intervals.searchsorted(zone, side="right")
            money_utility = 1 / b[i]
        self.mode_choice_param = cast(Dict[str, Dict[str, Any]], self.mode_choice_param) #type checker help
        money_utility /= next(iter(self.mode_choice_param.values()))["log"]["logsum"]
        accessibility = -money_utility * logsum
        return probs, accessibility

    def _calc_utils(self, impedance):
        self.dest_expsums = {}
        for mode in self.dest_choice_param:
            expsum = self._calc_dest_util(mode, impedance[mode])
            self.dest_expsums[mode] = {}
            self.dest_expsums[mode]["logsum"] = expsum
            label = self.purpose.name + "_" + mode
            logsum = pandas.Series(
                numpy.log(expsum), self.purpose.zone_numbers, name=label)
            self.zone_data._values[label] = logsum
        mode_expsum = self._calc_mode_util(self.dest_expsums)
        logsum = pandas.Series(
            numpy.log(mode_expsum), self.purpose.zone_numbers,
            name=self.purpose.name)
        self.zone_data._values[self.purpose.name] = logsum
        return mode_expsum

    def _calc_prob(self, mode_expsum):
        prob = {}
        for mode in self.mode_choice_param:
            mode_exps = self.mode_exps[mode]
            mode_prob = numpy.divide(
                mode_exps, mode_expsum, out=numpy.zeros_like(mode_exps),
                where=mode_expsum!=0)
            dest_exps = self._dest_exps[mode].T
            dest_expsum = self.dest_expsums[mode]["logsum"]
            dest_prob = numpy.divide(
                dest_exps, dest_expsum, out=numpy.zeros_like(dest_exps),
                where=dest_expsum!=0)
            prob[mode] = mode_prob * dest_prob
        return prob

    def _get_cost_util_coefficient(self):
        try:
            b = next(iter(self.dest_choice_param.values()))["impedance"]["cost"]
        except KeyError:
            # School tours do not have a constant cost parameter
            # Use value of time conversion from CBA guidelines instead
            b = -0.46738697
        return b


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
        mode_expsum = self._calc_utils(impedance)
        self._dest_exps.clear()
        self.accessibility = {}
        self.accessibility["all"] = self.zone_data[self.purpose.name]
        self.accessibility["sustainable"] = numpy.zeros_like(mode_expsum)
        self.accessibility["car"] = numpy.zeros_like(mode_expsum)
        for mode in self.mode_choice_param:
            logsum = self.zone_data[f"{self.purpose.name}_{mode}"]
            self.accessibility[mode] = logsum
            if mode.split('_')[0] == "car":
                self.accessibility["car"] += logsum
            else:
                self.accessibility["sustainable"] += numpy.log(self.mode_exps[mode])
        # Scale logsum value to eur
        b = self._get_cost_util_coefficient()
        try:
            money_utility = 1 / b
        except TypeError:  # Separate params for cap region and surrounding
            money_utility = 1 / b[0]
        money_utility /= next(iter(self.mode_choice_param.values()))["log"]["logsum"]
        for key in ["all", "sustainable", "car"]:
            self.accessibility[f"{key}_scaled"] = money_utility * self.accessibility[key]

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

    def _add_log_impedance(self, exps, impedance, b):
        """Adds log transformations of impedance to utility.

        This is an optimized way of calculating log terms. Calculates
        impedance1^b1 * ... * impedanceN^bN in the following equation:
        e^(linear_terms + b1*log(impedance1) + ... + bN*log(impedanceN))
        = e^(linear_terms) * impedance1^b1 * ... * impedanceN^bN

        If parameter in b is tuple of two terms,
        capital region will be picked.

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
                exps *= numpy.power(impedance[i] + 1, b[i])
            except ValueError: # Separate params for cap region and surrounding
                exps *= numpy.power(impedance[i] + 1, b[i][0])
        return exps

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
        logsum = {"logsum": mode_expsum}
        dest_expsum = self._calc_dest_util("logsum", logsum)
        prob = {}
        dest_prob = self._dest_exps["logsum"].T / dest_expsum
        for mode in self.mode_choice_param:
            mode_prob = (self.mode_exps[mode] / mode_expsum).T
            prob[mode] = mode_prob * dest_prob
        return prob


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
