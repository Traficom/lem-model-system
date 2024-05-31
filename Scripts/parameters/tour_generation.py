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
        "age_7-17": 0.0059,
        "age_18-29": 0.2794,
        "age_30-49": 0.3671,
        "age_50-64": 0.2904,
        "age_65-99": 0.0148
    },
    "hb_edu_basic": {
        "age_7-17": 0.3466,
        "age_18-29": 0,
        "age_30-49": 0,
        "age_50-64": 0,
        "age_65-99": 0
    },
    "hb_edu_upsec": {
        "age_7-17": 0.0369,
        "age_18-29": 0.0556,
        "age_30-49": 0.0056,
        "age_50-64": 0.0016,
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
        "age_7-17": 0.0656,
        "age_18-29": 0.1293,
        "age_30-49": 0.1363,
        "age_50-64": 0.1349,
        "age_65-99": 0.1964
    },
    "hb_other_shop": {
        "age_7-17": 0.0616,
        "age_18-29": 0.0805,
        "age_30-49": 0.1209,
        "age_50-64": 0.1457,
        "age_65-99": 0.1937
    },
    "hb_leisure": {
        "age_7-17": 0.1404,
        "age_18-29": 0.087,
        "age_30-49": 0.0971,
        "age_50-64": 0.1026,
        "age_65-99": 0.1161
    },
    "hb_sport": {
        "age_7-17": 0.1284,
        "age_18-29": 0.0566,
        "age_30-49": 0.0881,
        "age_50-64": 0.071,
        "age_65-99": 0.0554
    },
    "hb_visit": {
        "age_7-17": 0.1553,
        "age_18-29": 0.1488,
        "age_30-49": 0.0946,
        "age_50-64": 0.089,
        "age_65-99": 0.0933
    },
    "wb_business": {
        "hb_work": 0.0543
    },
    "wb_other": {
        "hb_work": 0.082
    },
    "ob_other": {
        "hb_edu_basic": 0.0353,
        "hb_edu_upsec": 0.0238,
        "hb_edu_higher": 0.0405,
        "hb_visit": 0.065
    },
    "hb_work_long": {
        "age_7-17_female": 0.0005,
        "age_7-17_male": 0.0001,
        "age_18-29_female":  0.0043,
        "age_18-29_male":  0.0062,
        "age_30-49_female":  0.0047,
        "age_30-49_male":  0.0113,
        "age_50-64_female":  0.0026,
        "age_50-64_male":  0.0061,
        "age_65-99_female":  0.0002,
        "age_65-99_male":  0.0004
    },
    "hb_business_long": {
        "income_0-19": 0.0004,
        "income_20-39": 0.0013,
        "income_40-59": 0.0024,
        "income_60-79": 0.0031,
        "income_80-99": 0.0055,
        "income_100": 0.0064
    },
    "hb_leisure_long": {
        "income_0-19": 0.0108,
        "income_20-39": 0.0134,
        "income_40-59": 0.0187,
        "income_60-79": 0.0193,
        "income_80-99": 0.0246,
        "income_100": 0.02432
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
