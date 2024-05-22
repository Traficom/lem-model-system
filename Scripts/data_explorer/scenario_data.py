
import os
import pandas as pd
import geopandas as gpd

from data_explorer.util import read_zone_data, read_zones
from datahandling.matrixdata import MatrixData

class ScenarioData(object):
    def __init__(self, name: str, results_path: str, input_path: str):
        """Container for result data of single scenario, which 
        also enables export to geopackage file format.

        Args:
            name : Scenario name
            results_path : Path to scenario results.
            zones_path : Path to model-system zones (geopackage)
        """
        name = name
        self.input_path = input_path
        self.zones = read_zones(input_path)
        self.results_path = results_path
        self.aggregations = read_zone_data(
            os.path.join(self.input_path, "admin_regions.agg"))
        self.accessibility = read_zone_data(
            os.path.join(self.results_path, "accessibility.txt"))
        self.demand = read_zone_data(
            os.path.join(self.results_path, "origins_demand.txt"))
        self.mode_shares = read_zone_data(
            os.path.join(self.results_path, "origins_shares.txt"))

    def zonedata_to_gdf(self, zonedata):
        return self.zones.merge(zonedata, on='zone_id', how='left')

    def zones_subregion(self, subregion_type, subregion):
        ids = self.aggregations.loc[self.aggregations[subregion_type] == subregion]["zone_id"]
        self.zones = self.zones.loc[self.zones.zone_id.isin(ids)]

    def read_costs(self, time_period, mtx_type, ass_class):
        """
        Read cost matrix from omx files.

        Parameters
        ----------
        time_period : str
            Time period (aht/pt/iht/vrk).
        mtx_type : str
            Matrix type (cost/dist/time).
        ass_class : str
            Assignment class of model (car/transit/bike/walk).

        Return
        ------
        matrix : numpy.matrix
            Cost matrix of mode and type.
        lookup : pandas.series
            Zone ids of matrix indices.
        """
        matrixdata = MatrixData(os.path.join(self.results_path, "Matrices"))
        with matrixdata.open(mtx_type, time_period) as mtx:
            matrix = mtx[ass_class]
            lookup = mtx.lookup
        return matrix, lookup
    
        
    def get_costs_from(self, time_period, mtx_type, ass_class, origin_zone):
        matrix, lookup = self.read_costs(time_period, ass_class, mtx_type)
        return pd.DataFrame(cost = matrix[:,lookup == origin_zone], index=lookup)

        