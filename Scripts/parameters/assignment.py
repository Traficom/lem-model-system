### ASSIGNMENT PARAMETERS ###

from collections import namedtuple
from typing import Dict, List, Union
RoadClass = namedtuple(
    "RoadClass",
    (
        "type", "num_lanes", "volume_delay_func", "lane_capacity",
        "free_flow_speed", "bus_delay",
    ))
# Code derived from three-digit link type xyz, where yz is the road class code
roadclasses = {
    1: RoadClass("motorway", "<3", 1, 2100, 113, 0.265),
    2: RoadClass("motorway", "<3", 1, 2100, 113, 0.265),
    3: RoadClass("motorway", ">=3", 1, 1900, 113, 0.265),
    4: RoadClass("motorway", "<3", 1, 2000, 97, 0.309),
    5: RoadClass("motorway", ">=3", 1, 1800, 97, 0.309),
    6: RoadClass("motorway", "<3", 1, 2000, 81, 0.370),
    7: RoadClass("motorway", ">=3", 1, 1800, 81, 0.370),
    8: RoadClass("highway", "any", 2, 1900, 97, 0.309),
    9: RoadClass("highway", "any", 2, 1700, 97, 0.309),
    10: RoadClass("highway", "any", 2, 1900, 90, 0.309),
    11: RoadClass("highway", "any", 2, 1700, 90, 0.309),
    12: RoadClass("highway", "any", 2, 1850, 81, 0.370),
    13: RoadClass("highway", "any", 2, 1650, 81, 0.370),
    14: RoadClass("highway", "any", 2, 1600, 73, 0.411),
    15: RoadClass("highway", "any", 2, 1500, 73, 0.411),
    16: RoadClass("highway", "any", 2, 1600, 63, 0.556),
    17: RoadClass("highway", "any", 2, 1400, 63, 0.556),
    18: RoadClass("arterial", "any", 3, 1400, 97, 0.309),
    19: RoadClass("arterial", "any", 3, 1400, 90, 0.309),
    20: RoadClass("arterial", "any", 3, 1350, 81, 0.370),
    21: RoadClass("arterial", "any", 3, 1450, 61, 0.492),
    22: RoadClass("arterial", "any", 3, 1100, 73, 0.492),
    23: RoadClass("arterial", "any", 3, 1250, 54, 0.556),
    24: RoadClass("arterial", "any", 3, 1100, 63, 0.492),
    25: RoadClass("arterial", "any", 4, 1150, 48, 0.625),
    26: RoadClass("arterial", "any", 4, 1050, 48, 0.625),
    27: RoadClass("arterial", "any", 4, 1000, 44, 0.682),
    28: RoadClass("arterial", "any", 4, 1000, 41, 0.732),
    29: RoadClass("arterial", "any", 4, 900, 41, 0.732),
    30: RoadClass("collector", "any", 5, 900, 48, 0.625),
    31: RoadClass("collector", "any", 5, 900, 41, 0.732),
    32: RoadClass("collector", "any", 5, 900, 36, 0.833),
    33: RoadClass("collector", "any", 5, 750, 36, 0.833),
    34: RoadClass("collector", "any", 5, 700, 41, 0.732),
    35: RoadClass("local", "any", 5, 700, 30, 1.000),
    36: RoadClass("local", "any", 5, 600, 30, 1.000),
    37: RoadClass("local", "any", 5, 500, 30, 1.000),
    38: RoadClass("local", "any", 5, 500, 23, 1.304),
    39: RoadClass("local", "any", 5, 700, 20, 1.304),
    40: RoadClass("local", "any", 5, 600, 20, 1.304),
    41: RoadClass("local", "any", 5, 500, 20, 1.304),
    44: RoadClass("ferry", "any", 11, 500, 20, 1.000),
}
connector_link_types = (84, 85, 86, 87, 88, 98, 99)
connector = RoadClass("connector", "any", 99, 0, 50, 0)
roadclasses.update({linktype: connector for linktype in connector_link_types})
custom_roadtypes = {
    91: "motorway",
    92: "highway",
    93: "arterial",
    94: "arterial",
    95: "local",
}
# Bike delay function ids
bikepath_vdfs = (
    {  # 0 - Mixed traffic
        None: 78,
        "collector": 77,
        "arterial": 77,
        "highway": 76,
    },
    {  # 1 - Bike lane
        None: 75,
    },
    {  # 2 - Road-side bike path
        None: 74,
        "arterial": 73,
        "highway": 72,
    },
    {  # 3 - Separate bike path
        None: 71
    },
    {  # 4 - BAANA
        None: 70,
    }
)
# Transit delay function ids
transit_delay_funcs = {
    ("bus", "bge"): {
        "no_buslane": 1,
        "buslane": 2,
    },
    ("rail", "rjmwtpl"): {
        "aht": 6,
        "pt": 6,
        "iht": 6,
        "it": 6,
        "vrk": 6,
    },
}
# Node numbers used in HSL official networks and their allowed modes
official_node_numbers = {
    "hcvkyasf": (1, 35000),
    "hcvkybgdewasf": (40000, 600000),
    "hmaf": (800000, 800500),
    "hrjasf": (801000, 801500),
    "htpaf": (802000, 806000),
    "hpaf": (810000, 816000),
}
vdf_temp = ("(put(60/ul2)*(1+{}*put((volau+volad)/{})/"
            + "(ul1-get(2))))*(get(2).le.put(ul1*{}))*length+(get(2).gt."
            + "get(3))*({}*get(1)*length+{}*(get(2)-get(3))*length)")
buslane = "((lanes-1).max.0.8)"
volume_delay_funcs = {
    # Car functions
    "fd1": vdf_temp.format(0.02, "lanes", 0.975, 1.78, 0.0075),
    "fd2": vdf_temp.format(0.09, "lanes", 0.935, 2.29, 0.0085),
    "fd3": vdf_temp.format(0.10, "lanes", 0.915, 2.08, 0.0110),
    "fd4": vdf_temp.format(0.20, "lanes", 0.870, 2.34, 0.0140),
    "fd5": vdf_temp.format(0.30, "lanes", 0.810, 2.28, 0.0170),
    "fd6": vdf_temp.format(0.02, buslane, 0.975, 1.78, 0.0075),
    "fd7": vdf_temp.format(0.09, buslane, 0.935, 2.29, 0.0085),
    "fd8": vdf_temp.format(0.10, buslane, 0.915, 2.08, 0.0110),
    "fd9": vdf_temp.format(0.20, buslane, 0.870, 2.34, 0.0140),
    "fd10": vdf_temp.format(0.3, buslane, 0.810, 2.28, 0.0170),
    "fd11": "length*(60/ul2)+el1",
    "fd90": "length*(60/ul2)",
    "fd91": "length*(60/ul2)",
    "fd99": "length*(60/ul2)",
    # Bike functions
    "fd70": "length*(60/19)",
    "fd71": "length*(60/17)",
    "fd72": "length*(60/17)",
    "fd73": "length*(60/16)",
    "fd74": "length*(60/15)",
    "fd75": "length*(60/15)",
    "fd76": "length*(60/12)",
    "fd77": "length*(60/10)",
    "fd78": "length*(60/12)",
    "fd98": "length*(60/12)",
    # Transit functions
    ## Bus, no bus lane, max speed set to 100 km/h
    "ft01": "timau.max.(length*0.6)",
    ## Bus on bus lane
    "ft02": "length*(60/ul2)",
    ## Tram aht
    "ft03": "(length / (int(ul1 / 10000))) * 60",
    ## Tram pt
    "ft04": "(length / ((int(ul1 / 100)) .mod. 100)) * 60",
    ## Tram iht
    "ft05": "(length / (ul1 .mod. 100)) * 60",
    ## Train functions
    "ft6": "us1",
    ## Escape function, speed 40 km/h
    "ft7": "length/(40/60)",
}
walk_speed = 5
# Network fields defining whether transit mode stops at node
stop_codes = {
    't': "#transit_stop_t",
    'p': "#transit_stop_p",
    'b': "#transit_stop_b",
    'g': "#transit_stop_g",
    'e': "#transit_stop_e",
}
# Default bus stop dwell time in minutes
bus_dwell_time = {
    'b': 0.4,
    'g': 0.4,
    'e': 0.4,
}
# Node labels for HSL members (new and old fare zones)
hsl_area = "ABCDE HEXL"
# Performance settings
performance_settings = {
    "number_of_processors": "max",
    "network_acceleration": True,
    "u_turns_allowed": True,
}
# Inversed value of time [min/eur]
vot_inv = {
    "work": 7.576, # 1 / ((7.92 eur/h) / (60 min/h)) = 7.576 min/eur
    "business": 2.439, # 1 / ((24.60 eur/h) / (60 min/h)) = 2.439 min/eur
    "leisure": 11.173, # 1 / ((5.37 eur/h) / (60 min/h)) = 11.173 min/eur
    "truck": 1.877, # 1 / ((31.96 eur/h) / (60 min/h)) = 1.877 min/eur
    "semi_trailer": 1.709, # 1 / ((35.11 eur/h) / (60 min/h)) = 1.709 min/eur
    "trailer_truck": 1.667, # 1 / ((36 eur/h) / (60 min/h)) = 1.667 min/eur
}
freight_terminal_cost = {
    'D': 0,
    'J': 0,
    'W': 0
}
# Boarding penalties for different transit modes
boarding_penalty = {
    'b': 3, # Bus
    'g': 3, # Trunk bus
    'd': 5, # Long-distance bus
    'e': 5, # Express bus
    't': 0, # Tram
    'p': 0, # Light rail
    'm': 0, # Metro
    'w': 0, # Ferry
    'r': 2, # Commuter train
    'j': 2, # Long-distance train
}
# Boarding penalties for end assignment
last_boarding_penalty = {
    'b': 5, # Bus
    'g': 2, # Trunk bus
    'd': 5, # Long-distance bus
    'e': 5, # Express bus
    't': 0, # Tram
    'p': 0, # Light rail
    'm': 0, # Metro
    'w': 0, # Ferry
    'r': 2, # Commuter train
    'j': 2, # Long-distance train
}
# Headway standard deviation function parameters for different transit modes
headway_sd_func = {
    'b': {
        "asc": 2.164,
        "ctime": 0.078,
        "cspeed": -0.028,
    },
    'd':  {
        "asc": 2.164,
        "ctime": 0.078,
        "cspeed": -0.028,
    },
    'g':  {
        "asc": 2.127,
        "ctime": 0.034,
        "cspeed": -0.021,
    },
    't':  {
        "asc": 1.442,
        "ctime": 0.060,
        "cspeed": -0.039,
    },
    'p':  {
        "asc": 1.442,
        "ctime": 0.034,
        "cspeed": -0.039,
    },
}
stopping_criteria = {
    "fine": {
        # Stopping criteria for last traffic assignment
        "max_iterations": 400,
        "relative_gap": 0.00001,
        "best_relative_gap": 0.001,
        "normalized_gap": 0.0005,
    },
    "coarse": {
        # Stopping criteria for traffic assignment in loop
        "max_iterations": 200,
        "relative_gap": 0.0001,
        "best_relative_gap": 0.01,
        "normalized_gap": 0.005,
    },
}
# Congestion function for congested transit assignment
trass_func = {
    "type": "BPR",
    "weight": 1.23,
    "exponent": 3,
    "assignment_period": 1,
    "orig_func": False,
    "congestion_attribute": "us3",
}
# Stopping criteria for congested transit assignment
trass_stop = {
    "max_iterations": 50,
    "normalized_gap": 0.01,
    "relative_gap": 0.001
}
# Specification for the transit assignment
transfer_penalty = {
    "transit_work": 3,
    "transit_leisure": 5,
    "car_first_mile": 5,
    "car_last_mile": 5,
    "transit": 5,
    "train": 10,
    "long_d_bus": 10,
    "airplane": 10,
}
extra_waiting_time = {
    "penalty": "@wait_time_dev",
    "perception_factor": 3.5
}
first_headway_fraction = 0.3
standard_headway_fraction = 0.5
waiting_time_perception_factor = 1.5
aux_transit_time = {
    "perception_factor": 1.75
}
aux_time_perception_factor_truck = 30
# Stochastic bike assignment distribution
bike_dist = {
    "type": "UNIFORM", 
    "A": 0.5, 
    "B": 1.5,
}
# Factors for 24-h expansion of volumes
# TODO: Trucks and vans
volume_factors = {
    "car": {
        "aht": 1. / 0.465,
        "pt": 1. / 0.094,
        "iht": 1. / 0.369,
    },
    "car_work": {
        "aht": 1. / 0.456,
        "pt": 1. / 0.102,
        "iht": 1. / 0.433,
    },
    "car_leisure": {
        "aht": 1. / 0.488,
        "pt": 1. / 0.089,
        "iht": 1. / 0.289,
    },
    "transit": {
        "aht": 1. / 0.478,
        "pt": 1. / 0.109,
        "iht": 1. / 0.405,
    },
    "transit_work": {
        "aht": 1. / 0.445,
        "pt": 1. / 0.103,
        "iht": 1. / 0.414,
    },
    "transit_leisure": {
        "aht": 1. / 0.571,
        "pt": 1. / 0.117,
        "iht": 1. / 0.373,
    },
    "car_first_mile": {
        "aht": 1. / 0.478,
        "pt": 1. / 0.109,
        "iht": 1. / 0.405,
    },
    "car_last_mile": {
        "aht": 1. / 0.478,
        "pt": 1. / 0.109,
        "iht": 1. / 0.405,
    },
    "train": {
        "aht": 2.8,
        "pt": 10,
        "iht": 3.4,
    },
    "long_d_bus": {
        "aht": 2.8,
        "pt": 10,
        "iht": 3.4,
    },
    "airplane": {
        "aht": 2.8,
        "pt": 10,
        "iht": 3.4,
    },
    "bike": {
        "aht": 1. / 0.604,
        "pt": 1. / 0.105,
        "iht": 1. / 0.430,
    },
    "bike_work": {
        "aht": 1. / 0.542,
        "pt": 1. / 0.109,
        "iht": 1. / 0.500,
    },
    "bike_leisure": {
        "aht": 1. / 0.725,
        "pt": 1. / 0.103,
        "iht": 1. / 0.332,
    },
    "trailer_truck": {
        "aht": 1 / 0.3,
        "pt": 1 / 0.1,
        "iht": 1 / 0.3,
    },
    "semi_trailer": {
        "aht": 1 / 0.3,
        "pt": 1 / 0.1,
        "iht": 1 / 0.3,
    },
    "truck": {
         "aht": 1 / 0.3,
        "pt": 1 / 0.1,
        "iht": 1 / 0.3,
    },
    "van": {
        "aht": 1 / 0.3,
        "pt": 1 / 0.1,
        "iht": 1 / 0.3,
    },
    "bus": {
        "aht": 1 / 0.497, 
        "pt": 1 / 0.090, 
        "iht": 1 / 0.497,
    },
}
volume_factors["aux_transit"] = volume_factors["transit"]
for mode in volume_factors:
        volume_factors[mode]["vrk"] = 1
        volume_factors[mode]["it"] = 0
# Factor for converting weekday traffic into yearly day average
years_average_day_factor = 0.85
# Factor for converting day traffic into 7:00-22:00 traffic
share_7_22_of_day = 0.9
# Effective headway as function of actual headway
effective_headway = {
    (0, 10): lambda x: 1.1*x,
    (10, 30): lambda x: 11 + 0.9*x,
    (30, 60): lambda x: 29 + 0.5*x,
    (60, 120): lambda x: 44 + 0.3*x,
    (120, float("inf")): lambda x: 62 + 0.2*x,
}
# Noise zone width as function of start noise
noise_zone_width = {
    (0, 55): lambda x: 5,
    (55, 65): lambda x: 10 + 31./10*x,
    (65, 68): lambda x: 41 + 16./3*x,
    (68, 71): lambda x: 57 + 21./3*x,
    (71, 74): lambda x: 78 + 31./3*x,
    (74, 77): lambda x: 109 + 44./3*x,
    (77, 80): lambda x: 153 + 66./3*x,
    (80, float("inf")): lambda x: 225,
}

### ASSIGNMENT REFERENCES ###
time_periods = {
    "aht": "AssignmentPeriod",
    "pt": "OffPeakPeriod",
    "iht": "AssignmentPeriod",
    "it": "TransitAssignmentPeriod",
}
car_classes = (
    "car_work",
    "car_leisure",
)
car_and_van_classes = car_classes + ("van",)
private_classes = car_and_van_classes + ("bike",)
park_and_ride_classes = (
    # "car_first_mile",
    # "car_last_mile",
)
long_distance_transit_classes = park_and_ride_classes + (
    "train",
    "long_d_bus",
    "airplane",
)
local_transit_classes = (
    "transit_work",
    "transit_leisure",
)
transit_classes = local_transit_classes + long_distance_transit_classes
truck_classes = (
    "truck",
    "semi_trailer",
    "trailer_truck",
)
transport_classes = private_classes + transit_classes + truck_classes
assignment_classes = {
    "hb_work": "work",
    "hb_edu_basic": "work",
    "hb_edu_student": "work",
    "hb_grocery": "leisure",
    "hb_other_shop": "leisure",
    "hb_leisure": "leisure",
    "hb_sport": "leisure",
    "hb_visit": "leisure",
    "hb_overnight": "leisure",
    "hb_business": "work",
    "wb_business": "work",
    "wb_other": "leisure",
    "ob_other": "leisure",
    "hb_work_long": "work",
    "hb_business_long": "work",
    "hb_private_day": "leisure",
    "hb_private_week": "leisure",
    "external": "leisure",
}
main_mode = 'h'
bike_mode = 'f'
assignment_modes = {
    "car_work": 'c',
    "car_leisure": 'c',
    "trailer_truck": 'y',
    "semi_trailer": 'y',
    "truck": 'k',
    "van": 'v',
}
vot_classes = {
    "car_work": "work",
    "car_leisure": "leisure",
    "trailer_truck": "trailer_truck",
    "semi_trailer": "semi_trailer",
    "truck": "truck",
    "van": "business",
    "transit_work": "work",
    "transit_leisure": "leisure",
    "car_first_mile": "work",
    "car_last_mile": "work",
    "train": "work",
    "long_d_bus": "leisure",
    "airplane": "work",
}
local_transit_modes = [
    'b',
    'g',
    'm',
    'p',
    'r',
    't',
    'w',
]
long_dist_transit_modes = {
  	"transit_work": ['e', 'j', 'l'],
    "transit_leisure": ['e', 'j', 'l'],
    "car_first_mile": ['e', 'j', 'l'],
    "car_last_mile": ['e', 'j', 'l'],
    "train": ['j'],
    "long_d_bus": ['e'],
    "airplane": ['l'],
}
aux_modes = [
    'a',
]
park_and_ride_mode = 'u'
freight_modes = {
    "freight_train": {
        'D': "@diesel_train",
        'J': "@electric_train",
    },
    "ship": {
        'W': "@ship",
    },
}
external_modes = [
    "car_leisure",
    "transit_leisure",
    "truck",
    "trailer_truck",
]
segment_results = {
    "transit_volumes": "vol",
    "total_boardings": "boa",
    "transfer_boardings": "trb",
}
uncongested_transit_time = "base_timtr"
impedance_output = ["time", "cost", "dist", "toll_cost", "inv_time"]
transit_impedance_matrices = {
    "total": {
        "unweighted_time": "total_travel_time",
        "tw_time": "actual_total_waiting_times",
        "fw_time": "actual_first_waiting_times",
    },
    "by_mode_subset": {
        "inv_time": "actual_in_vehicle_times",
        "aux_time": "actual_aux_transit_times",
        "board_time": "actual_total_boarding_times",
    },
    "local": {
        "loc_bc": "actual_total_boarding_costs",
        "loc_ic": "actual_in_vehicle_costs",
        "loc_time": "actual_in_vehicle_times",
    },
}
background_traffic_attr = "ul3"
transit_delay_attr = "us1"
line_penalty_attr = "us2"
line_operator_attr = "ut1"
effective_headway_attr = "ut2"
boarding_penalty_attr = "@boa_"
dist_fare_attr = "@dist_fare"
board_fare_attr = "@board_fare"
board_long_dist_attr = "@board_long_dist"
is_in_transit_zone_attr = "ui1"
keep_stops_attr = "#keep_stops"
subarea_attr = "#subarea"
municipality_attr = "#municipality"
terminal_cost_attr = "@freight_term_cost"
freight_gate_attr = "@freight_gate"
ferry_wait_attr = "@ferry_wait_time"
extra_freight_cost_attr = "#extra_cost"
railtypes = {
    2: "tram",
    3: "metro",
    4: "train",
    5: "tram",
    6: "tram",
}
roadtypes = {
    0: "walkway",
    1: "motorway",
    2: "multi-lane",
    3: "multi-lane",
    4: "single-lane",
    5: "single-lane",
    11: "ferry",
    99: "connector",
}
station_ids = {
    "metro": 13,
    "train": 14,
}
