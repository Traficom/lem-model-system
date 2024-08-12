# Share of demand that will be simulated in agent model
from typing import Any, Dict, List, Tuple, Union

# O-D pairs with demand below threshold are neglected in sec dest calculation
secondary_destination_threshold = 0.1

agent_demand_fraction = 1.0

# Seed number for population attributes:
# int = fixed seed and same population for each run
# None = different population for each run
population_draw = 31

# Age groups in zone data
age_groups: List[Tuple[int, int]] = [ #changed to list for type checker
        (7, 17),
        (18, 29),
        (30, 49),
        (50, 64),
        (65, 99),
]

### DEMAND MODEL REFERENCES ###

# Tour purpose zone intervals
# Some demand models have separate sub-region parameters,
# hence need sub-intervals defined.
purpose_areas: Dict[str, Union[Tuple[int,int],Tuple[int,int,int]]] = {
    "metropolitan": (0, 2000, 35000),
    "peripheral": (35001, 36000),
    "all": (0, 2000, 36000),
    "external": (36000, 40000),
}
purpose_matrix_aggregation_level = "area"
tour_length_intervals = (0, 3, 5, 10, 20, 30, 40, 100,
                         200, 400, 600, 800, float("inf"))
# Population in noise zones as share of total area population as
# function only of zone area, calculated by Ramboll Feb 2021
pop_share_per_noise_area = {
    "helsinki_cbd": 0.028816313,
    "helsinki_other": 0.005536503,
    "espoo_vant_kau": 0.002148004,
    "surround_train": 0.0019966,
    "surround_other": 0.001407824,
    "peripheral": 0,  # Not calculated
}

export_zdata = [
    "population", "age_7-17", "age_18-29", "age_50-64", "age_65-99", 
    "income_0-19", "income_20-39", "income_40-59", "income_60-79", 
    "income_80-99", "income_100", "workplaces", "sports_in", "sports_out",
    "area_education", "area_leisure", "service", "shop", "hospitality",
    "recreation", "park_cost", "park_time", "comprehensive",
    "upper_secondary", "higher_education", "building_dist"
]
