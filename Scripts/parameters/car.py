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
cars_hh1 = {
    0: {
        "constant": 0.0,
        "generation": {},
        "individual_dummy": {
            "sh_income_0_19": 0,
            "sh_income_20_39": 0,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
    },
    1: {
        "constant": 3.182379,
        "generation": {
            "hb_leisure_sustainable": -0.417948,
            "sh_row_or_detached": 1.284792,
        },
        "individual_dummy": {
            "sh_income_0_19": -2.589644,
            "sh_income_20_39": -1.030502,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
    },
    2: {
        "constant": 3.257525,
        "generation": {
            "hb_leisure_sustainable": -1.170948,
            "sh_row_or_detached": 1.284792,
        },
        "individual_dummy": {
            "sh_income_0_19": -2.589644,
            "sh_income_20_39": -1.030502,
            "sh_income_40_59": 1.325116,
            "sh_income_60_79": 1.964296,
            "sh_income_80_99": 2.356314,
            "sh_income_100_": 2.917251
        },
    }
}

cars_hh2 = {
    0: {
        "constant": 0.0,
        "generation": {},
        "individual_dummy": {
            "sh_income_0_19": 0,
            "sh_income_20_39": 0,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
    },
    1: {
        "constant": 3.182379,
        "generation": {
            "hb_leisure_sustainable": -0.417948,
            "sh_row_or_detached": 1.284792,
        },
        "individual_dummy": {
            "sh_income_0_19": -2.589644,
            "sh_income_20_39": -1.030502,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
    },
    2: {
        "constant": 3.257525,
        "generation": {
            "hb_leisure_sustainable": -1.170948,
            "sh_row_or_detached": 1.284792,
        },
        "individual_dummy": {
            "sh_income_0_19": -2.589644,
            "sh_income_20_39": -1.030502,
            "sh_income_40_59": 1.325116,
            "sh_income_60_79": 1.964296,
            "sh_income_80_99": 2.356314,
            "sh_income_100_": 2.917251
        },
    }
}

cars_hh3 = {
    0: {
        "constant": 0.0,
        "generation": {},
        "individual_dummy": {
            "sh_income_0_19": 0,
            "sh_income_20_39": 0,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
    },
    1: {
        "constant": 3.182379,
        "generation": {
            "hb_leisure_sustainable": -0.417948,
            "sh_row_or_detached": 1.284792,
        },
        "individual_dummy": {
            "sh_income_0_19": -2.589644,
            "sh_income_20_39": -1.030502,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
    },
    2: {
        "constant": 3.257525,
        "generation": {
            "hb_leisure_sustainable": -1.170948,
            "sh_row_or_detached": 1.284792,
        },
        "individual_dummy": {
            "sh_income_0_19": -2.589644,
            "sh_income_20_39": -1.030502,
            "sh_income_40_59": 1.325116,
            "sh_income_60_79": 1.964296,
            "sh_income_80_99": 2.356314,
            "sh_income_100_": 2.917251
        },
    }
}