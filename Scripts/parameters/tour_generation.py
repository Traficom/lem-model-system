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
        "age_30_49": 0.3645,
        "age_50_64": 0.2926,
        "age_65_99": 0.0156
    },
    "hb_edu_basic": {
        "age_7_17": 0.3804,
        "age_18_29": 0.0026,
        "age_30_49": 0.0047,
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
        "age_7_17": 0.0647,
        "age_18_29": 0.1355,
        "age_30_49": 0.1426,
        "age_50_64": 0.1394,
        "age_65_99": 0.2062
    },
    "hb_other_shop": {
        "age_7_17": 0.0581,
        "age_18_29": 0.0754,
        "age_30_49": 0.1236,
        "age_50_64": 0.1516,
        "age_65_99": 0.1818
    },
    "hb_leisure": {
        "age_7_17": 0.1433,
        "age_18_29": 0.0914,
        "age_30_49": 0.102,
        "age_50_64": 0.1056,
        "age_65_99": 0.1187
    },
    "hb_sport": {
        "age_7_17": 0.1482,
        "age_18_29": 0.0708,
        "age_30_49": 0.0931,
        "age_50_64": 0.0676,
        "age_65_99": 0.0545
    },
    "hb_visit": {
        "age_7_17": 0.1603,
        "age_18_29": 0.1501,
        "age_30_49": 0.111,
        "age_50_64": 0.1281,
        "age_65_99": 0.1368
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
        "hb_edu_student": 0.0405,
        "hb_visit": 0.065
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
