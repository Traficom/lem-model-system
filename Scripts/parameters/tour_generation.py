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
            "constant":   14.64,
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
        ("hb_edu_higher",) : {
            "constant":   2.512,
            "individual_dummy": {
                "age_7_17": 0.0,
                "age_18_29":  4.958,
                "age_30_49":  2.652,
                "age_50_64": 0.0,
                "age_65_99": 0.0
            },
            "zone": {
                "hb_edu_higher": .4611
            }
        }
    },
    2: {
        ("hb_edu_higher", "hb_edu_higher") : {
            "constant":   0.0,
            "individual_dummy": {
                "age_7_17": 0.0,
                "age_18_29":  4.958,
                "age_30_49":  2.652,
                "age_50_64": 0.0,
                "age_65_99": 0.0
            },
            "zone": {
                "hb_edu_higher": .4166
            }
        }
    }
}

tour_conditions = {}

tour_generation = {
    "hb_work": {
        "age_7_17": 0.0059,
        "age_18_29": 0.2794,
        "age_30_49": 0.3671,
        "age_50_64": 0.2904,
        "age_65_99": 0.0148
    },
    "hb_edu_basic": {
        "age_7_17": 0.3466,
        "age_18_29": 0,
        "age_30_49": 0,
        "age_50_64": 0,
        "age_65_99": 0
    },
    "hb_edu_upsec": {
        "age_7_17": 0.0369,
        "age_18_29": 0.0556,
        "age_30_49": 0.0056,
        "age_50_64": 0.0016,
        "age_65_99": 0
    },
    "hb_edu_higher": {
        "age_7_17": 0.0,
        "age_18_29": 0.0,
        "age_30_49": 0.0,
        "age_50_64": 0.0,
        "age_65_99": 0.0
    },
    "hb_grocery": {
        "age_7_17": 0.0656,
        "age_18_29": 0.1293,
        "age_30_49": 0.1363,
        "age_50_64": 0.1349,
        "age_65_99": 0.1964
    },
    "hb_other_shop": {
        "age_7_17": 0.0616,
        "age_18_29": 0.0805,
        "age_30_49": 0.1209,
        "age_50_64": 0.1457,
        "age_65_99": 0.1937
    },
    "hb_leisure": {
        "age_7_17": 0.1404,
        "age_18_29": 0.087,
        "age_30_49": 0.0971,
        "age_50_64": 0.1026,
        "age_65_99": 0.1161
    },
    "hb_sport": {
        "age_7_17": 0.1284,
        "age_18_29": 0.0566,
        "age_30_49": 0.0881,
        "age_50_64": 0.071,
        "age_65_99": 0.0554
    },
    "hb_visit": {
        "age_7_17": 0.1553,
        "age_18_29": 0.1488,
        "age_30_49": 0.0946,
        "age_50_64": 0.089,
        "age_65_99": 0.0933
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
        "population_Uusimaa": 0.00268,
        "population_Lounais-Suomi": 0.00532,
        "population_Ita-Suomi": 0.00449,
        "population_Pohjois-Suomi": 0.00472
    },
    "hb_business_long": {
        "population_Uusimaa": 0.00129,
        "population_Lounais-Suomi": 0.00334,
        "population_Ita-Suomi": 0.00283,
        "population_Pohjois-Suomi": 0.00185
    },
    "hb_leisure_long": {
        "population_Uusimaa": 0.01741,
        "population_Lounais-Suomi": 0.01518,
        "population_Ita-Suomi": 0.01812,
        "population_Pohjois-Suomi": 0.01874
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
