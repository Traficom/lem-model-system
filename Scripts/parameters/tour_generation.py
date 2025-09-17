### TOUR GENERATION PARAMETERS ####

tour_combination_area = "all"
# Scale parameter used in upper level of tour pattern model
tour_number_scale = 1.0
# Calibration of tour numbers
tour_number_increase = {
    1: 1.0,
    2: 1.0,
    3: 1.0,
}
# Tour combinations (calibrated)
tour_combinations = {
    0: {
        () : {
            "constant":   0,
            "individual_dummy": {
                "age_7_17": 0.0,
                "age_18_29":  0.0,
                "age_30_49":  0.0,
                "age_50_64": 0.0,
                "age_65_99": 0.0
            },
            "zone": {}
        }
# utility function 2
    },
    1: {
        ("hb_edu_student",) : {
            "constant":   -2.538089,
            "individual_dummy": {
                "age_7_17": 1.208474,
                "age_18_29": 0.0,
                "age_30_49": -2.230785,
                "age_50_64": -2.817654,
                "age_65_99": -4.072479
            },
            "zone": {
                "hb_edu_student": .397998,
                "log_pop_density": -0.167866
            }
        }
    }
}

tour_conditions = {}

tour_generation = {
    "hb_work": {
        "age_7_17": 0.0046,
        "age_18_29": 0.2808,
        "age_30_49": 0.393,
        "age_50_64": 0.3071,
        "age_65_99": 0.0149
    },
    "hb_edu_basic": {
        "age_7_17": 0.396,
        "age_18_29": 0.0024,
        "age_30_49": 0.0077,
        "age_50_64": 0.0003,
        "age_65_99": 0.0005
    },
    "hb_edu_student": {
        "age_7_17": 0.0,
        "age_18_29": 0.0,
        "age_30_49": 0.0,
        "age_50_64": 0.0,
        "age_65_99": 0.0,
    },
    "hb_grocery": {
        "age_7_17": 0.0694,
        "age_18_29": 0.1286,
        "age_30_49": 0.1305,
        "age_50_64": 0.1427,
        "age_65_99": 0.2136
    },
    "hb_other_shop": {
        "age_7_17": 0.069,
        "age_18_29": 0.0884,
        "age_30_49": 0.1283,
        "age_50_64": 0.1451,
        "age_65_99": 0.2089
    },
    "hb_leisure": {
        "age_7_17": 0.1512,
        "age_18_29": 0.0936,
        "age_30_49": 0.1036,
        "age_50_64": 0.1174,
        "age_65_99": 0.1316
    },
    "hb_sport": {
        "age_7_17": 0.1535,
        "age_18_29": 0.0724,
        "age_30_49": 0.096,
        "age_50_64": 0.0647,
        "age_65_99": 0.0545
    },
    "hb_visit": {
        "age_7_17": 0.1351,
        "age_18_29": 0.1081,
        "age_30_49": 0.0808,
        "age_50_64": 0.0863,
        "age_65_99": 0.0947
    },
    "hb_business": {
        "age_7_17": 0.0045,
        "age_18_29": 0.0461,
        "age_30_49": 0.0554,
        "age_50_64": 0.0492,
        "age_65_99": 0.017
    },
    "hb_leisure_overnight": {
        "age_7_17": 0.0357,
        "age_18_29": 0.052,
        "age_30_49": 0.0279,
        "age_50_64": 0.0375,
        "age_65_99": 0.0299
    },
    "wb_business": {
        "hb_work": 0.0454
    },
    "wb_other": {
        "hb_work": 0.0687,
        "hb_edu_basic": 0.0362,
        "hb_edu_student": 0.0295
    },
    "ob_other": {
        "hb_leisure": 0.0206,
        "hb_sport": 0.0107,
        "hb_visit": 0.0544
    },
    "truck": {
        "population": 0.01,
        "workplaces": 0.025,
        "logistics": 0.35,
        "industry": 0.035,
        "shop": 0.05,
    },
    "trailer_truck": {
        "population": None,
        "workplaces": 0.005,
        "logistics": 0.38,
        "industry": 0.038,
        "shop": 0.005,
    }
}
garbage_generation = {
    "population": 0.000125,
    "workplaces": 0.000025,
}
vector_calibration_threshold = 5
