from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, Tuple
import numpy # type: ignore
import pandas
import utils.log as log
if TYPE_CHECKING:
    from datahandling.resultdata import ResultsData
    from datahandling.zonedata import ZoneData

from models.logit import LogitModel
from parameters.car import car_ownership

def divide(a, b):
    return numpy.divide(a, b, out=numpy.zeros_like(a), where=b!=0)

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
                 zone_data: ZoneData, 
                 bounds: slice, 
                 resultdata: ResultsData):
        self.resultdata = resultdata
        self.zone_data = zone_data
        self.bounds = bounds
        self.param = car_ownership

    def calc_basic_prob(self) -> numpy.ndarray:
        prob = {}
        self.exps = {}
        nr_cars_expsum = 0
        # First calc probabilites without individual dummies
        for nr_cars in self.param:
            b = self.param[nr_cars]
            utility = numpy.zeros(self.bounds.stop, dtype=numpy.float32)
            self._add_constant(utility, b["constant"])
            utility = self._add_zone_util(utility, b["generation"], True)
            self.exps[nr_cars] = numpy.exp(utility)
            nr_cars_expsum += numpy.exp(utility)
        for nr_cars in self.param:
            prob[nr_cars] = divide(self.exps[nr_cars], nr_cars_expsum)
        return prob


    def calc_prob(self) -> pandas.Series:
        """Calculate car user probabilities with individual dummies included.

        Returns
        -------
        pandas.Series
                Choice probabilities
        """
        prob = self.calc_basic_prob()
        # Calculate probability within individual dummies and combine
        nr_cars_expsum = numpy.zeros(self.bounds.stop, dtype=numpy.float32)
        for nr_cars in self.param:
            for dummy in self.param[nr_cars]["individual_dummy"]:
                ind_prob = {}
                b = self.param[nr_cars]["individual_dummy"][dummy]
                dummy_share = self.zone_data.get_data(dummy, self.bounds, generation=True)
                try:
                    self.exps[nr_cars] *= numpy.exp(b)
                except ValueError:
                    for i, bounds in enumerate(self.bounds):
                        self.exps[nr_cars][bounds] *= numpy.exp(b[i])
            nr_cars_expsum += self.exps[nr_cars]
        for nr_cars in self.param:
            ind_prob = self.exps[nr_cars] / nr_cars_expsum
            no_dummy = (1 - dummy_share) * prob[nr_cars]
            dummy = dummy_share * ind_prob
            prob[nr_cars] = no_dummy + dummy
        # Calculate car density
        population = self.zone_data["population"]
        households = divide(population, self.zone_data["avg_household_size"])
        cars = numpy.zeros_like(population)
        for nr_cars in self.param:
            cars += prob[nr_cars] * households * nr_cars
        prob["cars"] = pandas.Series(
            cars, self.zone_data.zone_numbers[self.bounds], name="cars")
        prob["car_density"] = pandas.Series(
            divide(cars, population), self.zone_data.zone_numbers[self.bounds], name="car_density")
        for nr_cars in self.param:
            prob["sh_cars" + nr_cars] = prob.pop(nr_cars)
        self.resultdata.print_data(prob, "zone_car_ownership.txt")
        return prob["car_density"]

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
        numpy.ndarray
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
