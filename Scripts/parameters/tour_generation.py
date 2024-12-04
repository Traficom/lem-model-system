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
        "age_18_29": 0.2645,
        "age_30_49": 0.3549,
        "age_50_64": 0.2785,
        "age_65_99": 0.0143
    },
    "hb_edu_basic": {
        "age_7_17": 0.3254,
        "age_18_29": 0,
        "age_30_49": 0,
        "age_50_64": 0,
        "age_65_99": 0
    },
    "hb_edu_upsec": {
        "age_7_17": 0.0296,
        "age_18_29": 0.0513,
        "age_30_49": 0.0031,
        "age_50_64": 0.0011,
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
        "age_18_29": 0.1268,
        "age_30_49": 0.133,
        "age_50_64": 0.1316,
        "age_65_99": 0.1948
    },
    "hb_other_shop": {
        "age_7_17": 0.0586,
        "age_18_29": 0.0781,
        "age_30_49": 0.1185,
        "age_50_64": 0.1433,
        "age_65_99": 0.19
    },
    "hb_leisure": {
        "age_7_17": 0.1341,
        "age_18_29": 0.0827,
        "age_30_49": 0.0934,
        "age_50_64": 0.0989,
        "age_65_99": 0.1141
    },
    "hb_sport": {
        "age_7_17": 0.1282,
        "age_18_29": 0.0565,
        "age_30_49": 0.0868,
        "age_50_64": 0.0673,
        "age_65_99": 0.0545
    },
    "hb_visit": {
        "age_7_17": 0.1406,
        "age_18_29": 0.121,
        "age_30_49": 0.0858,
        "age_50_64": 0.0802,
        "age_65_99": 0.0896
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
    "hb_private_day": {
        "income_0_19": 0.00339,
        "income_20_39": 0.00502,
        "income_40_59": 0.00708,
        "income_60_79": 0.00744,
        "income_80_99": 0.00892,
        "income_100_": 0.00762
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
