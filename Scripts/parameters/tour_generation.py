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
        "age_18_29": 0.2677,
        "age_30_49": 0.3642,
        "age_50_64": 0.2926,
        "age_65_99": 0.0156
    },
    "hb_edu_basic": {
        "age_7_17": 0.3736,
        "age_18_29": 0.0026,
        "age_30_49": 0.0085,
        "age_50_64": 0,
        "age_65_99": 0
    },
    "hb_edu_student": {
        "age_7_17": 0.0,
        "age_18_29": 0.0,
        "age_30_49": 0.0,
        "age_50_64": 0.0,
        "age_65_99": 0.0
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
        "age_7_17": 0.1429,
        "age_18_29": 0.091,
        "age_30_49": 0.0961,
        "age_50_64": 0.1015,
        "age_65_99": 0.1123
    },
    "hb_sport": {
        "age_7_17": 0.1467,
        "age_18_29": 0.07,
        "age_30_49": 0.0925,
        "age_50_64": 0.0668,
        "age_65_99": 0.0542
    },
    "hb_visit": {
        "age_7_17": 0.1461,
        "age_18_29": 0.1352,
        "age_30_49": 0.0948,
        "age_50_64": 0.0966,
        "age_65_99": 0.0944
    },
    "hb_business": {
        "age_7_17": 0.0013,
        "age_18_29": 0.0275,
        "age_30_49": 0.0453,
        "age_50_64": 0.0383,
        "age_65_99": 0.0155
    },
    "hb_overnight": {
        "age_7_17": 0.0144,
        "age_18_29": 0.0172,
        "age_30_49": 0.0197,
        "age_50_64": 0.0372,
        "age_65_99": 0.0503
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
        "hb_visit": 0.0281,
        "hb_overnight": 0.0346
    },
    "hb_work_long": {
        "age_7_17": 0.00019,
        "age_18_29": 0.00238,
        "age_30_49": 0.00275,
        "age_50_64": 0.00223,
        "age_65_99": 0.0001
    },
    "hb_business_long": {
        "age_7_17": 0.0000,
        "age_18_29": 0.00036,
        "age_30_49": 0.00287,
        "age_50_64": 0.00119,
        "age_65_99": 0.00027
    },
    "hb_private_day": {
        "income_0_19": 0.00263,
        "income_20_39": 0.00319,
        "income_40_59": 0.00415,
        "income_60_79": 0.00481,
        "income_80_99": 0.00633,
        "income_100_": 0.0058
    },
    "hb_private_week": {
        "income_0_19": 0.00632,
        "income_20_39": 0.0069,
        "income_40_59": 0.01044,
        "income_60_79": 0.01059,
        "income_80_99": 0.01404,
        "income_100_": 0.01448
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
