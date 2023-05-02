import pandas
import numpy

from datatypes.demand import Demand
from datatypes.purpose import Purpose
from utils.zone_interval import ZoneIntervals


class ExternalModel:
    """External traffic model.

    Parameters
    ----------
    base_demand : datahandling.matrixdata.MatrixData
        Base demand matrices
    zone_data : datahandling.zonedata.ZoneData
        Zone data for forecast year
    zone_numbers : numpy.ndarray
        Zone numbers from assignment model
    """

    def __init__(self, base_demand, zone_data, zone_numbers):
        self.base_demand = base_demand
        self.all_zone_numbers = zone_numbers
        self.growth = zone_data.externalgrowth
        spec = {
            "name": "external",
            "orig": None,
            "dest": None,
            "area": "external",
        }
        self.purpose = Purpose(spec, zone_data)

    def calc_external(self, mode, internal_trips):
        """Calculate external traffic.

        Parameters
        ----------
        mode : str
            Travel mode (car/transit/truck/trailer_truck)
        internal_trips : pandas.Series
            Sums of all (intra-area) trips to and frome zones
        
        Return
        ------
        Demand
            Matrix of whole day trips from external to internal zones
        """
        mtx = pandas.DataFrame(0, self.all_zone_numbers, self.growth.index)
        return Demand(self.purpose, mode, mtx.to_numpy().T)
