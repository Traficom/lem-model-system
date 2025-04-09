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
        "calibration": {
            "constant": 0.351746493
        }
    },
    1: {
        "constant": 1.340137,
        "generation": {
            "hb_leisure_sustainable": 0.205013,
            "hb_leisure_car_leisure": -0.205013,
            "sh_row_or_detached": 1.904786,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.916330,
            "sh_income_20_39": -0.712555,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
        "calibration": {
            "constant": -0.258168917
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
        "calibration": {
            "constant": 0.0000762998
        }
    },
    1: {
        "constant": 2.162438,
        "generation": {
            "hb_leisure_sustainable": 0.198998,
            "hb_leisure_car_leisure": -0.198998,
            "sh_row_or_detached": 2.494079,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.949738,
            "sh_income_20_39": -0.651540,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
        "calibration": {
            "constant": -0.053030492
        }
    },
    2: {
        "constant": 1.190672,
        "generation": {
            "hb_leisure_sustainable": 0.568111,
            "hb_leisure_car_leisure": -0.568111,
            "sh_row_or_detached": 4.741679,
        },
        "individual_dummy": {
            "sh_income_0_19": -3.083747,
            "sh_income_20_39": -1.299364,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0.377211,
            "sh_income_80_99": 0.660624,
            "sh_income_100_": 1.084823
        },
        "calibration": {
            "constant": 0.106509189
        }
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
        "calibration": {
            "constant": -0.040299362
        }
    },
    1: {
        "constant": 2.39324,
        "generation": {
            "hb_leisure_sustainable": 0.198998,
            "hb_leisure_car_leisure": -0.198998,
            "sh_row_or_detached": 2.494079,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.949738,
            "sh_income_20_39": -0.651540,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
        "calibration": {
            "constant": -0.126889775
        }
    },
    2: {
        "constant": 2.220873,
        "generation": {
            "hb_leisure_sustainable": 0.568111,
            "hb_leisure_car_leisure": -0.568111,
            "sh_row_or_detached": 4.741679,
        },
        "individual_dummy": {
            "sh_income_0_19": -3.083747,
            "sh_income_20_39": -1.299364,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0.377211,
            "sh_income_80_99": 0.660624,
            "sh_income_100_": 1.084823
        },
        "calibration": {
            "constant": 0.114047282
        }
    }
}