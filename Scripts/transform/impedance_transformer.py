from collections import defaultdict
import numpy # type: ignore

import parameters.assignment as param


class ImpedanceTransformer:
    def __init__(self, purpose, parameters):
        self.name = purpose.name
        self.bounds = purpose.bounds
        self.zone_data = purpose.zone_data
        self.impedance_share = parameters

    def transform(self, impedance):
        """Perform transformation from time period dependent matrices 
        to aggregate impedance matrices for specific travel purpose.

        Transform transit costs from (eur/month) to (eur/day).

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
            Mode (car/transit/bike/walk) : dict
                Type (time/cost/dist) : numpy 2-d matrix
        """
        rows = self.bounds
        cols = (self.bounds if self.name == "hoo"
            else slice(0, self.zone_data.nr_zones))
        day_imp = {}
        for mode in self.impedance_share:
            day_imp[mode] = defaultdict(float)
            if mode in param.divided_classes:
                ass_class = "{}_{}".format(
                    mode, param.assignment_classes[self.name])
            else:
                ass_class = mode
            for time_period in impedance:
                for mtx_type in impedance[time_period]:
                    if ass_class in impedance[time_period][mtx_type]:
                        share = self.impedance_share[mode][time_period]
                        imp = impedance[time_period][mtx_type][ass_class]
                        day_imp[mode][mtx_type] += share[0] * imp[rows, cols]
                        day_imp[mode][mtx_type] += share[1] * imp[cols, rows].T
        return day_imp
