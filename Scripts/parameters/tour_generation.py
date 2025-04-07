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
            "constant":   8.587,
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
            "constant":   3.948,
            "individual_dummy": {
                "age_7_17": 0.0,
                "age_18_29": 1.982,
                "age_30_49": 0.1045,
                "age_50_64": 0.0,
                "age_65_99": 0.0
            },
            "zone": {
                "hb_edu_student": .1260
            }
        }
    },
    2: {
        ("hb_edu_student", "hb_edu_student") : {
            "constant":   0.0,
            "individual_dummy": {
                "age_7_17": 0.0,
                "age_18_29": 1.982,
                "age_30_49": 0.1045,
                "age_50_64": 0.0,
                "age_65_99": 0.0
            },
            "zone": {
                "hb_edu_student": .2786
            }
        }
    }
}

tour_conditions = {}

tour_generation = {
    "hb_work": {
        "age_7_17": 0.0062,
        "age_18_29": 0.268,
        "age_30_49": 0.3679,
        "age_50_64": 0.2943,
        "age_65_99": 0.0158
    },
    "hb_edu_basic": {
        "age_7_17": 0.3736,
        "age_18_29": 0.0026,
        "age_30_49": 0.0085,
        "age_50_64": 0,
        "age_65_99": 0
    },
    "hb_edu_student": {
        "age_7_17": 0.0353,
        "age_18_29": 0.1366,
        "age_30_49": 0.0223,
        "age_50_64": 0.0066,
        "age_65_99": 0.0026
    },
    "hb_grocery": {
        "age_7_17": 0.0632,
        "age_18_29": 0.1345,
        "age_30_49": 0.141,
        "age_50_64": 0.1383,
        "age_65_99": 0.2035
    },
    "hb_other_shop": {
        "age_7_17": 0.056,
        "age_18_29": 0.075,
        "age_30_49": 0.121,
        "age_50_64": 0.1494,
        "age_65_99": 0.1806
    },
    "hb_leisure": {
        "age_7_17": 0.1439,
        "age_18_29": 0.0915,
        "age_30_49": 0.0989,
        "age_50_64": 0.1022,
        "age_65_99": 0.1143
    },
    "hb_sport": {
        "age_7_17": 0.1467,
        "age_18_29": 0.0703,
        "age_30_49": 0.0939,
        "age_50_64": 0.0668,
        "age_65_99": 0.0542
    },
    "hb_visit": {
        "age_7_17": 0.1495,
        "age_18_29": 0.1412,
        "age_30_49": 0.1003,
        "age_50_64": 0.1012,
        "age_65_99": 0.0979
    },
    "hb_business": {
        "age_7_17": 0.0013,
        "age_18_29": 0.0275,
        "age_30_49": 0.0453,
        "age_50_64": 0.0383,
        "age_65_99": 0.0155
    },
    "wb_business": {
        "hb_work": 0.0367
    },
    "wb_other": {
        "hb_work": 0.0618,
        "hb_business": 0.0295,
        "hb_edu_basic": 0.0303,
        "hb_edu_student": 0.0363
    },
    "ob_other": {
        "hb_leisure": 0.0184,
        "hb_sport": 0.0061,
        "hb_visit": 0.0281
    },
    "hb_business_long": {
        "population_Uusimaa": 0.00129,
        "population_Lounais-Suomi": 0.00334,
        "population_Ita-Suomi": 0.00283,
        "population_Pohjois-Suomi": 0.00185
    },
    "hb_private_week": {
        "income_0_19": 0.00786,
        "income_20_39": 0.00836,
        "income_40_59": 0.01183,
        "income_60_79": 0.01246,
        "income_80_99": 0.0155,
        "income_100_": 0.01712
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
