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
            "constant":   13.75,
            "individual_dummy": {},
            "zone": {}
        }
# utility function 2
    },
    1: {
        ("hb_edu_higher",) : {
            "constant":   3.318,
            "individual_dummy": {
                "age_7-17": 0.0,
                "age_18-29":  4.996,
                "age_30-49":  2.735,
                "age_50-64": 0.0,
                "age_65-99": 0.0
            },
            "zone": {
                "hb_edu_higher_t": .3595
            }
        }
    },
    2: {
        ("hb_edu_higher", "hb_edu_higher") : {
            "constant":   0.0,
            "individual_dummy": {
                "age_7-17": 0.0,
                "age_18-29":  4.996,
                "age_30-49":  2.735,
                "age_50-64": 0.0,
                "age_65-99": 0.0
            },
            "zone": {
                "hb_edu_higher_t": .4302
            }
        }
    }
}

tour_conditions = {}

tour_generation = {
    "hb_work": {
        "age_7-17": 0.0101,
        "age_18-29": 0.3529,
        "age_30-49": 0.5299,
        "age_50-64": 0.4065,
        "age_65-99": 0.0335

    },
    "hb_edu_basic": {
        "age_7-17": 0.4412,
        "age_18-29": 0,
        "age_30-49": 0,
        "age_50-64": 0,
        "age_65-99": 0
    },
    "hb_edu_upsec": {
        "age_7-17": 0.0455,
        "age_18-29": 0.0738,
        "age_30-49": 0.0072,
        "age_50-64": 0.0024,
        "age_65-99": 0
    },
    "hb_edu_higher": {
        "age_7-17": 0.0,
        "age_18-29": 0.0,
        "age_30-49": 0.0,
        "age_50-64": 0.0,
        "age_65-99": 0.0
    },
    "hb_grocery": {
        "age_7-17": 0.0511,
        "age_18-29": 0.1192,
        "age_30-49": 0.1185,
        "age_50-64": 0.1264,
        "age_65-99": 0.1937
    },
    "hb_other_shop": {
        "age_7-17": 0.0526,
        "age_18-29": 0.0737,
        "age_30-49": 0.1032,
        "age_50-64": 0.1429,
        "age_65-99": 0.2118
    },
    "hb_leisure": {
        "age_7-17": 0.137,
        "age_18-29": 0.0897,
        "age_30-49": 0.0848,
        "age_50-64": 0.0888,
        "age_65-99": 0.11
    },
    "hb_sport": {
        "age_7-17": 0.1079,
        "age_18-29": 0.0545,
        "age_30-49": 0.0671,
        "age_50-64": 0.0552,
        "age_65-99": 0.0414
    },
    "hb_visit": {
        "age_7-17": 0.1184,
        "age_18-29": 0.1106,
        "age_30-49": 0.0703,
        "age_50-64": 0.0784,
        "age_65-99": 0.0999
    },
    "wb_business": {
        "hb_work": 0.0543
    },
    "wb_other": {
    "hb_work": 0.0716
    },
    "ob_other": {
        "hb_edu_basic": 0.0357,
        "hb_edu_upsec": 0.0234,
        "hb_edu_higher": 0.0422,
        "hb_visit": 0.0066
    },
    "hb_work_long": {
        "age_7-17_female": 0.0005,
        "age_7-17_male": 0.0001,
        "age_18-29_female":  0.0044,
        "age_18-29_male":  0.0071,
        "age_30-49_female":  0.005,
        "age_30-49_male":  0.0118,
        "age_50-64_female":  0.0027,
        "age_50-64_male":  0.0067,
        "age_65-99_female":  0.0002,
        "age_65-99_male":  0.0004
    },
    "hb_business_long": {
        "income_0-19": 0.0004,
        "income_20-39": 0.0011,
        "income_40-59": 0.0021,
        "income_60-79": 0.0032,
        "income_80-99": 0.0058,
        "income_100": 0.0068
    },
    "hb_leisure_long": {
        "income_0-19": 0.0122,
        "income_20-39": 0.0147,
        "income_40-59": 0.0222,
        "income_60-79": 0.0228,
        "income_80-99": 0.0264,
        "income_100": 0.027
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
tour_weights = {
    "hb_work": 1,
    "hb_edu_basic": 1,
    "hb_edu_upsec": 1,
    "hb_edu_higher": 1,
    "hb_grocery": 1,
    "hb_other_shop": 1,
    "hb_sport": 1,
    "hb_visit": 1,
    "hb_work_long": 1,
    "hb_business_long": 1,
    "hb_leisure_long": 1
}
garbage_generation = {
    "population": 0.000125,
    "workplaces": 0.000025,
}
vector_calibration_threshold = 5
