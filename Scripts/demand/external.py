from __future__ import annotations
from typing import TYPE_CHECKING
import pandas
import numpy # type: ignore
if TYPE_CHECKING:
    from datahandling.matrixdata import MatrixData
    from datahandling.zonedata import ZoneData

from datatypes.demand import Demand
from datatypes.purpose import Purpose
from parameters.departure_time import demand_share


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

    def __init__(self, 
                 base_demand: MatrixData, 
                 zone_data: ZoneData, 
                 zone_numbers: numpy.array):
        self.base_demand = base_demand
        self.all_zone_numbers = zone_numbers
        self.growth = zone_data.externalgrowth
        spec = {
            "name": "external",
            "orig": None,
            "dest": None,
            "area": "all",
            "impedance_share": None,
            "impedance_transform": None,
            "demand_share": demand_share["external"]
        }
        self.purpose = Purpose(spec, zone_data)

    def calc_external(self, mode: str, internal_trips: pandas.Series) -> Demand:
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
