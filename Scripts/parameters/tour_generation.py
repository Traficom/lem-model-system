### TOUR GENERATION PARAMETERS ####

tour_combination_area = "domestic"
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
            "constant":   6.051171,
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
            "constant":   0.0,
            "individual_dummy": {
                "age_7_17": 2.516453,
                "age_18_29": 3.286894,
                "age_30_49": 1.412812,
                "age_50_64": 0.0,
                "age_65_99": 0.0
            },
            "zone": {
                "hb_edu_student": 0.143613
            }
        }
    }
}

tour_conditions = {}

vector_calibration_threshold = 5
