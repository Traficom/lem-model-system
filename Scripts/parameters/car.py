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
            "constant": 0.0
        }
    },
    1: {
        "constant": 1.425544,
        "generation": {
            "hb_leisure_sustainable": -0.196968,
            "sh_row_or_detached": 1.274938,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.930154,
            "sh_income_20_39": -0.701987,
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
        "constant": 2.868101,
        "generation": {
            "hb_leisure_sustainable": -0.346655,
            "sh_row_or_detached": 1.529165,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.997633,
            "sh_income_20_39": -0.698690,
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
        "constant": 1.638978,
        "generation": {
            "hb_leisure_sustainable": -0.594442,
            "sh_row_or_detached": 2.944721,
        },
        "individual_dummy": {
            "sh_income_0_19": -3.341688,
            "sh_income_20_39": -1.389355,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0.405490,
            "sh_income_80_99": 0.684946,
            "sh_income_100_": 1.110711
        },
        "calibration": {
            "constant": 0.0
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
            "constant": 0.0
        }
    },
    1: {
        "constant": 3.039326,
        "generation": {
            "hb_leisure_sustainable": -0.346655,
            "sh_row_or_detached": 1.529165,
        },
        "individual_dummy": {
            "sh_income_0_19": -1.997633,
            "sh_income_20_39": -0.698690,
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
        "constant": 2.593503,
        "generation": {
            "hb_leisure_sustainable": -0.594442,
            "sh_row_or_detached": 2.944721,
        },
        "individual_dummy": {
            "sh_income_0_19": -3.341688,
            "sh_income_20_39": -1.389355,
            "sh_income_40_59": 0,
            "sh_income_60_79": 0.405490,
            "sh_income_80_99": 0.684946,
            "sh_income_100_": 1.110711
        },
        "calibration": {
            "constant": 0.0
        }
    }
}