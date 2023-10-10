from __future__ import annotations
from typing import TYPE_CHECKING
import numpy # type: ignore
import pandas
if TYPE_CHECKING:
    from datahandling.matrixdata import MatrixData
    from datahandling.zonedata import ZoneData

import parameters.tour_generation as param
from utils.freight import fratar, calibrate
from datatypes.demand import Demand
from datatypes.purpose import Purpose


class FreightModel:
    """Freight traffic model.

    Parameters
    ----------
    zone_data_base : datahandling.zonedata.ZoneData
        Zone data for base year
    zone_data_forecast : datahandling.zonedata.ZoneData
        Zone data for forecast year
    base_demand : datahandling.matrixdata.MatrixData
        Base demand matrices
    """

    def __init__(self, 
                 zone_data_base: ZoneData, 
                 zone_data_forecast: ZoneData, 
                 base_demand: MatrixData):
        self.zdata_b = zone_data_base
        self.zdata_f = zone_data_forecast
        self.base_demand = base_demand
        spec = {
            "name": "freight",
            "orig": None,
            "dest": None,
            "area": "all",
            "impedance_share": None,
        }
        self.purpose = Purpose(spec, zone_data_base)

    def calc_freight_traffic(self, mode: str) -> Demand:
        """Calculate freight traffic matrix.

        Parameters
        ----------
        mode : str
            Freight mode (truck/trailer_truck)

        Return
        ------
        datatypes.demand.Demand
            Freight mode demand matrix for whole day
        """
        zone_numbers = self.zdata_b.zone_numbers
        demand = pandas.DataFrame(0, zone_numbers, zone_numbers)
        return Demand(self.purpose, mode, demand.values)
