from parameters import impedance_share, first_peripheral_zone, first_external_zone, tour_purposes

class ImpedanceTransformer:
    def transform(self, purpose, impedance):
        """Perform transformation from time period dependent matrices 
        to aggregate impedance matrices for specific travel purpose.

        Parameters
        ----------
        purpose : TourPurpose
        impedance: dict
            Time period (aht/pt/iht) : dict
                Type (time/cost/dist) : dict
                    Assignment class (car_work/transit/...) : numpy 2d matrix
        Return 
        ------
        dict 
            Mode (car/transit/bike) : dict
                Type (time/cost/dist) : numpy 2d matrix
        """
        if purpose.name == "hoo":
            r_0 = 0
            r_n = purpose.zone_data.nr_zones
        else:
            r_0, r_n = purpose.bounds
        c_n = purpose.zone_data.nr_zones
        day_imp = {}
        for mode in impedance_share[purpose.name]:
            day_imp[mode] = {}
            if mode == "car":
                if purpose.dest == "work":
                    ass_class = "car_work"
                else:
                    ass_class = "car_leisure"
            else:
                ass_class = mode
            for idx, time_period in enumerate(impedance):
                for mtx_type in impedance[time_period]:
                    if ass_class in impedance[time_period][mtx_type]:
                        share = impedance_share[purpose.name][mode][time_period]
                        imp = impedance[time_period][mtx_type][ass_class][r_0:r_n, 0:c_n]
                        if idx == 0:
                            day_imp[mode][mtx_type] = share[0] * imp
                        else:
                            day_imp[mode][mtx_type] += share[0] * imp
                        imp = impedance[time_period][mtx_type][ass_class][0:c_n, r_0:r_n]
                        day_imp[mode][mtx_type] += share[1] * imp.T
        return day_imp