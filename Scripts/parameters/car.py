### CAR DENSITY AND USAGE PARAMETERS ###

# Driver share of car tours
# Inverse of car occupancy
from typing import Any, Dict, Tuple, Union


car_driver_share = { }

car_usage: Dict[str,Any] = {
    "constant": 0.0,
    "generation": {},
    "log": { },
    "individual_dummy": { },
}
car_density = {
    "constant": 0.0,
    "generation": { },
    "log": { },
}
car_ownership = {
    0: {
        "constant": 0.0,
        "generation": {},
        "individual_dummy": {},
    },
    1: {
        "constant": 2.568245,
        "generation": {
            "hb_leisure_sustainable": -0.476655,
            "sh_row_or_detached": 1.116087,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.645065,
            "sh_income_20_39": -0.167748,
            "sh_income_40_59": 0.669643,
            "sh_income_60_79": 1.235251,
            "sh_income_80_99": 0.991755,
            "sh_income_100_": 1.484410
        },
    },
    2: {
        "constant": 2.794911,
        "generation": {
            "hb_leisure_sustainable": -1.061793,
            "sh_row_or_detached": 2.127492,
        },
        "individual_dummy": {
            "sh_income_0_19": -3.653949,
            "sh_income_20_39": -1.191287,
            "sh_income_40_59": 0.714940,
            "sh_income_60_79": 1.869940,
            "sh_income_80_99": 2.020383,
            "sh_income_100_": 3.034884
        },
    }
}