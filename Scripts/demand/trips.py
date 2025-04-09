from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Tuple, List, cast
import numpy # type: ignore
import pandas
if TYPE_CHECKING:
    from datahandling.resultdata import ResultsData
    from datahandling.zonedata import ZoneData
    from datatypes.purpose import TourPurpose
from datatypes.person import Person

import utils.log as log
import parameters.zone as param
from parameters.tour_generation import tour_combination_area
from datatypes.purpose import SecDestPurpose
from models import car_use, car_ownership, linear, tour_combinations
from parameters.car import cars_hh1, cars_hh2, cars_hh3



class DemandModel:
    """Container for private tour purposes and models.

    Parameters
    ----------
    zone_data : ZoneData
        Data used for all demand calculations
    resultdata : ResultData
        Writer object to result directory
    tour_purposes : list of TourPurpose and SecDestPurpose instances
        Tour purposes
    is_agent_model : bool (optional)
        Whether the model is used for agent-based simulation
    """
    
    def __init__(self, 
                 zone_data: ZoneData, 
                 resultdata: ResultsData,
                 tour_purposes: List[TourPurpose],
                 is_agent_model: bool=False):
        self.resultdata = resultdata
        self.zone_data = zone_data
        self.tour_purposes = tour_purposes
        self.purpose_dict = {purpose.name: purpose for purpose in tour_purposes}
        for purpose in tour_purposes:
            try:
                sources = purpose.sources
            except AttributeError:
                pass
            else:
                purpose.sources = [self.purpose_dict[source] for source in sources]
                if isinstance(purpose, SecDestPurpose):
                    for source in purpose.sources:
                        source.sec_dest_purpose = purpose
        bounds = param.purpose_areas[tour_combination_area]
        self.bounds = slice(*zone_data.all_zone_numbers.searchsorted(
            [bounds[0], bounds[-1]]))
        self.car_use_model = car_use.CarUseModel(
            zone_data, self.bounds, param.age_groups, self.resultdata)
        self.car_ownership_models = {
            "hh1": car_ownership.CarOwnershipModel(cars_hh1, zone_data, 
                                            self.bounds, self.resultdata),
            "hh2": car_ownership.CarOwnershipModel(cars_hh2, zone_data, 
                                            self.bounds, self.resultdata),
            "hh3": car_ownership.CarOwnershipModel(cars_hh3, zone_data, 
                                            self.bounds, self.resultdata)
        }
    
        self.tour_generation_model = tour_combinations.TourCombinationModel(
            self.zone_data)
        # Income models used only in agent modelling
        self._income_models = [
            linear.IncomeModel(
                self.zone_data, self.bounds,
                self.resultdata, param.age_groups, is_helsinki=False),
            linear.IncomeModel(
                self.zone_data, self.bounds,
                self.resultdata, param.age_groups, is_helsinki=True),
        ]
        if is_agent_model:
            self.create_population()

    def _age_strings(self):
        for age_group in param.age_groups:
            yield "age_{}_{}".format(*age_group)

    def create_population_segments(self):
        """Create population segments.

        Store dict of dicts of `pandas.Series`, where each series is a
        zone array with number of people belonging to segment.
        Upper-level dict keys are age group strings (age_7-17/...).
        Lower-level dict keys are strings car_user and no_car.
        """
        cm = self.car_use_model
        self.zone_data["car_users"] = cm.calc_prob()
        self.segments = {}
        pop = self.zone_data["population"][self.bounds]
        for age in self._age_strings():
            age_pop = self.zone_data["sh_" + age][self.bounds] * pop
            car_share = sum(self.zone_data["share_" + gender][self.bounds]
                            * cm.calc_individual_prob(age, gender)
                for gender in cm.genders)
            self.segments[age] = {
                "car_users": car_share * age_pop,
                "no_car": (1-car_share) * age_pop,
            }

    def create_population(self):
        """Create population for agent-based simulation.

        Store list of `Person` instances in `self.population`.
        """
        numpy.random.seed(param.population_draw)
        self.population = []
        zone_numbers = self.zone_data.zone_numbers[self.bounds]
        self.zone_population = pandas.Series(0, zone_numbers)
        # Group -1 is under-7-year-olds
        age_range = numpy.arange(-1, len(param.age_groups))
        for zone_number in zone_numbers:
            weights = [self.zone_data[f"share_{age}"][zone_number]
                for age in self._age_strings()]
            # Append under-7 weight
            weights = [max(1 - sum(weights), 0)] + weights
            if sum(weights) > 1:
                if sum(weights) > 1.005:
                    msg = "Sum of age group shares for zone {} is {}".format(
                        zone_number, sum(weights))
                    log.error(msg)
                    raise ValueError(msg)
                else:
                    weights = numpy.array(weights)
                    rebalance = 1 / sum(weights)
                    weights = rebalance * weights
            zone_pop = int(round(self.zone_data["population"][zone_number]
                                 * param.agent_demand_fraction))
            zone = self.zone_data.zones[zone_number]
            incmod = self._income_models[zone.municipality == "Helsinki"]
            for _ in range(zone_pop):
                i = numpy.random.choice(a=age_range, p=weights)
                if i != -1:
                    self.population.append(Person(
                        zone, param.age_groups[i], self.tour_generation_model,
                        self.car_use_model, incmod))
                    self.zone_population[zone_number] += 1
        numpy.random.seed(None)

    def predict_income(self):
        for model in self._income_models:
            model.predict()

    def generate_tours(self):
        """Generate vector of tours for each tour purpose.

        Not used in agent-based simulation.
        Result is stored in `purpose.gen_model.tours`.
        """
        gm = self.tour_generation_model
        combination_purposes = {purpose for combination in gm.tour_combinations
            for purpose in combination}
        use_tour_combination_model = False
        for purpose in self.tour_purposes:
            purpose.gen_model.init_tours()
            if not isinstance(purpose, SecDestPurpose):
                purpose.gen_model.add_tours()
            if purpose.name in combination_purposes:
                use_tour_combination_model = True
        if use_tour_combination_model:
            self._generate_tour_combinations()

    def _generate_tour_combinations(self):
        gm = self.tour_generation_model
        for age in self._age_strings():
            segments = self.segments[age]
            prob_c = gm.calc_prob(age, is_car_user=True, zones=self.bounds)
            prob_n = gm.calc_prob(age, is_car_user=False, zones=self.bounds)
            nr_tours_sums = pandas.Series(name="nr_tours")
            for combination in prob_c:
                # Each combination is a tuple of tours performed during a day
                nr_tours = ( prob_c[combination] * segments["car_users"]
                           + prob_n[combination] * segments["no_car"])
                for purpose in combination:
                    try:
                        self.purpose_dict[purpose].gen_model.tours += nr_tours
                    except KeyError:
                        pass
                nr_tours_sums["-".join(combination)] = nr_tours.sum()

    def generate_tour_probs(self) -> Dict[Tuple[int,int], numpy.ndarray]:
        """Generate matrices of cumulative tour combination probabilities.

        Used in agent-based simulation.

        Returns
        -------
        dict
            Age (age_7-17/...) : tuple
                Is car user (False/True) : numpy.array
                    Matrix with cumulative tour combination probabilities
                    for all zones
        """
        probs = {}
        for age in self._age_strings():
            probs[age] = [self._get_probs(age, is_car_user)
                for is_car_user in (False, True)]
        return probs

    def _get_probs(self, age: str, is_car_user: bool) -> pandas.DataFrame:
        probs = self.tour_generation_model.calc_prob(
            age, is_car_user, self.bounds)
        return pandas.DataFrame(probs).to_numpy().cumsum(axis=1)
    
    def calculate_car_ownership(self, impedance):
        acc_purpose = self.purpose_dict["hb_leisure"]
        purpose_impedance = acc_purpose.transform_impedance(impedance)
        acc_purpose.accessibility_model.calc_accessibility(purpose_impedance)
        zd = self.zone_data
        prob = {hh_size: model.calc_prob()
            for hh_size, model in self.car_ownership_models.items()}
        zd["sh_cars1_hh1"] = zd["pop_sh_hh1"]*prob["hh1"][1]
        zd["sh_cars1_hh2"] = (zd["pop_sh_hh2"]*prob["hh2"][1]
                              + zd["pop_sh_hh3"]*prob["hh3"][1])
        zd["sh_cars2_hh2"] = (zd["pop_sh_hh2"]*prob["hh2"][2]
                              + zd["pop_sh_hh3"]*prob["hh3"][2])
        result = {"cars": numpy.zeros_like(zd["population"])}
        for n_cars in range(3):
            result[f"sh_cars{n_cars}"] = numpy.zeros_like(zd["population"])
            for hh_size in prob:
                if n_cars in prob[hh_size]:
                    hh_car = prob[hh_size][n_cars] * zd[hh_size]
                    result["cars"] += hh_car * n_cars
                    national_share = sum(hh_car) / sum(zd[hh_size])
                    self.resultdata.print_line(
                        f"{hh_size},cars{n_cars},{national_share}", "car_ownership")
                    result[f"sh_cars{n_cars}"] += prob[hh_size][n_cars] * zd[f"sh_{hh_size}"]                
        self.resultdata.print_data(result, "zone_car_ownership.txt")
