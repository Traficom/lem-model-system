from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Optional
import numpy # type: ignore
if TYPE_CHECKING:
    from datahandling.resultdata import ResultsData
    from datahandling.zonedata import ZoneData

from models.logit import LogitModel, divide
from utils.calibrate import attempt_calibration


class CarOwnershipModel(LogitModel):
    """Binary logit model for car use.

    Parameters
    ----------
    zone_data : ZoneData
        Data used for all demand calculations
    bounds : slice
        Zone bounds
    age_groups : list
        tuple
            int
                Age intervals
    resultdata : ResultData
        Writer object to result directory
    """

    def __init__(self, 
                 parameters: dict,
                 zone_data: ZoneData, 
                 bounds: slice, 
                 resultdata: ResultsData):
        self.resultdata = resultdata
        self.zone_data = zone_data
        self.bounds = bounds
        attempt_calibration(parameters)
        self.param = parameters

    def calc_basic_prob(self) -> Dict[int, numpy.ndarray]:
        prob = {}
        self.exps = {}
        nr_cars_expsum = 0
        # First calc probabilites without individual dummies
        for nr_cars in self.param:
            b = self.param[nr_cars]
            utility = numpy.zeros(self.bounds.stop, dtype=numpy.float32)
            utility += b["constant"]
            utility = self._add_zone_util(utility, b["generation"], True)
            self.exps[nr_cars] = numpy.minimum(numpy.exp(utility), 99999)
            nr_cars_expsum += self.exps[nr_cars]
        for nr_cars in self.param:
            prob[nr_cars] = divide(self.exps[nr_cars], nr_cars_expsum)
        return prob


    def calc_prob(self) -> Dict[int, numpy.ndarray]:
        """Calculate car user probabilities with individual dummies included.

        Returns
        -------
        dict
            key : int
                Number of cars in household (0, 1, 2(+))
            value : numpy.ndarray
                Choice probabilities
        """
        self.calc_basic_prob()
        prob = {}
        for nr_cars in self.param:
            prob[nr_cars] = numpy.zeros(self.bounds.stop, dtype=numpy.float32)
        # Calculate probability with individual dummies and combine
        for dummy in self.param[0]["individual_dummy"]:
            nr_cars_exp = {}
            nr_cars_expsum = numpy.zeros(self.bounds.stop, dtype=numpy.float32)
            for nr_cars in self.param:
                b = self.param[nr_cars]["individual_dummy"][dummy]
                nr_cars_exp[nr_cars] = self.exps[nr_cars] * numpy.exp(b)
                nr_cars_expsum += nr_cars_exp[nr_cars]
            for nr_cars in self.param:
                ind_prob = nr_cars_exp[nr_cars] / nr_cars_expsum
                dummy_share = self.zone_data.get_data(
                    dummy, self.bounds, generation=True)
                with_dummy = dummy_share * ind_prob
                prob[nr_cars] += with_dummy
        return prob

    def calc_individual_prob(self, 
                             income: str, 
                             gender: str, 
                             zone: Optional[int] = None):
        """Calculate car ownership probability with individual dummies included.

        Uses results from previously run `calc_basic_prob()`.

        Parameters
        ----------
        income : str
            Agent/segment income group
        gender : str
            Agent/segment gender (female/male)
        zone : int (optional)
            Index of zone where the agent lives, if no zone index is given,
            calculation is done for all zones

        Returns
        -------
        dict
            key : int
                Number of cars in household (0, 1, 2(+))
            value : numpy.ndarray
                Choice probabilities
        """
        prob = {}
        exps = {}
        nr_cars_expsum = 0
        for nr_cars in self.param:
            if zone is None:
                exps[nr_cars] = self.exps[nr_cars]
            else:
                exps[nr_cars] = self.exps[nr_cars][self.zone_data.zone_index(zone)]
            b = self.param
            if income in b["individual_dummy"]:
                exps[nr_cars] *= numpy.exp(b["individual_dummy"][income])
            if gender in b["individual_dummy"]:
                exps[nr_cars] *= numpy.exp(b["individual_dummy"][gender])
            nr_cars_expsum += exps[nr_cars]
        for nr_cars in self.param:
            prob = exps[nr_cars] / nr_cars_expsum
        return prob
