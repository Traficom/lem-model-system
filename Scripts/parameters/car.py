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
        "log_generation": {},
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
            "constant": 0.0
        }
    },
    1: {
        "constant": 3.221865,
        "log_generation": {},
        "generation": {
            "hb_leisure_sustainable": -0.099956,
            "sh_row_or_detached": 0.723959,
            "avg_park_time": -0.213470
        },
        "individual_dummy": {
            "sh_income_0_19": -2.003805,
            "sh_income_20_39": -0.761191,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
        "calibration": {
            "constant": 0.0
        },
    }
}

cars_hh2 = {
    0: {
        "constant": 0.0,
        "log_generation": {},
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
            "constant": 0.0
        }
    },
    1: {
        "constant": 46.473448,
        "log_generation": {
            "hb_leisure_sustainable": -11.631960
        },
        "generation": {
            "sh_row_or_detached": 1.288564,
            "avg_park_time": -0.090125
        },
        "individual_dummy": {
            "sh_income_0_19": -2.028729,
            "sh_income_20_39": -0.734470,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
        "calibration": {
            "constant": 0.0
        }
    },
    2: {
        "constant": 5.380774,
        "log_generation": {},
        "generation": {
            "hb_leisure_sustainable": -0.474514,
            "sh_row_or_detached": 1.850552,
            "avg_park_time": -0.450428
        },
        "individual_dummy": {
            "sh_income_0_19": -3.337603,
            "sh_income_20_39": -1.430880,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0.425441,
            "sh_income_80_99": 0.732656,
            "sh_income_100_": 1.248988
        },
        "calibration": {
            "constant": 0.0
        }
    }
}

cars_hh3 = {
    0: {
        "constant": 0.0,
        "log_generation": {},
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
            "constant": 0.0
        }
    },
    1: {
        "constant": 46.64258,
        "log_generation": {
            "hb_leisure_sustainable": -11.631960
        },
        "generation": {
            "sh_row_or_detached": 1.288564,
            "avg_park_time": -0.090125
        },
        "individual_dummy": {
            "sh_income_0_19": -2.028729,
            "sh_income_20_39": -0.734470,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0,
            "sh_income_80_99": 0,
            "sh_income_100_": 0
        },
        "calibration": {
            "constant": 0.0
        }
    },
    2: {
        "constant": 6.32751,
        "log_generation": {},
        "generation": {
            "hb_leisure_sustainable": -0.474514,
            "sh_row_or_detached": 1.850552,
            "avg_park_time": -0.450428
        },
        "individual_dummy": {
            "sh_income_0_19": -3.337603,
            "sh_income_20_39": -1.430880,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0.425441,
            "sh_income_80_99": 0.732656,
            "sh_income_100_": 1.248988
        },
        "calibration": {
            "constant": 0.0
        }
    }
}