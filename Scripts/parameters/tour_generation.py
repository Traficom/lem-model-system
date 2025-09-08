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

vector_calibration_threshold = 5
