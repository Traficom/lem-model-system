### DEPARTURE TIME PARAMETERS ###

# Demand shares for different time periods
from typing import Any, Dict


demand_share: Dict[str,Dict[str,Any]] = {
    "freight": {
        "trailer_truck": {
            "aht": (0.066, 0),
            "pt": (0.07, 0),
            "iht": (0.066, 0),
            "it": (0.0, 0.0),
        },
        "truck": {
            "aht": (0.066, 0),
            "pt": (0.07, 0),
            "iht": (0.066, 0),
            "it": (0.0, 0.0),
        },
        "van": {
            # As shares of car traffic
            # On top of this, the trucks sum is added
            "aht": (0.054, 0),
            "pt": (0.07, 0),
            "iht": (0.044, 0),
            "it": (0.0, 0.0),
        },
    },
    "external": {
        "car_work": {
            "aht": (0.042, 0.028),
            "pt": (0.05, 0.05),
            "iht": (0.045, 0.055),
            "it": (0.0, 0.0),
        },
        "car_leisure": {
            "aht": (0.042, 0.028),
            "pt": (0.05, 0.05),
            "iht": (0.045, 0.055),
            "it": (0.0, 0.0),
        },
        "car_electric": {
            "aht": (0.042, 0.028),
            "pt": (0.05, 0.05),
            "iht": (0.045, 0.055),
            "it": (0.0, 0.0),
        },
        "train": {
            "aht": (0.101, 0.034),
            "pt": (0.05, 0.05),
            "iht": (0.064, 0.119),
            "it": (0.0, 0.0),
        },
        "airplane": {
            "aht": (0.101, 0.034),
            "pt": (0.05, 0.05),
            "iht": (0.064, 0.119),
            "it": (0.0, 0.0),
        },
        "long_d_bus": {
            "aht": (0.101, 0.034),
            "pt": (0.05, 0.05),
            "iht": (0.064, 0.119),
            "it": (0.0, 0.0),
        },
        "trailer_truck": {
            "aht": (0.033, 0.033),
            "pt": (0.035, 0.035),
            "iht": (0.033, 0.033),
            "it": (0.0, 0.0),
        },
        "semi_trailer": {
            "aht": (0.033, 0.033),
            "pt": (0.035, 0.035),
            "iht": (0.033, 0.033),
            "it": (0.0, 0.0),
        },
        "truck": {
            "aht": (0.033, 0.033),
            "pt": (0.035, 0.035),
            "iht": (0.033, 0.033),
            "it": (0.0, 0.0),
        },
    },
}
for purpose in demand_share:
    for mode in demand_share[purpose]:
        demand_share[purpose][mode]["vrk"] = (((1, 1), (1, 1))
            if purpose == "hoo" else (1, 1))
backup_demand_share = {
    "aht": (0.042, 0.028),
    "pt": (0.05, 0.05),
    "iht": (0.045, 0.055),
}
