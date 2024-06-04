
import os
import pandas as pd
import geopandas as gpd
from typing import Optional

from datahandling.matrixdata import MatrixData

CRS = "EPSG:3067"
def read_spatial(path: str, file_name: str) -> gpd.GeoDataFrame:
    # Check that paths are valid
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Directory {path} does not exist.")
    files = os.listdir(path)
    if file_name not in files:
        raise FileNotFoundError(f"File {file_name} not found. Available files: {files}")
    data = gpd.read_file(os.path.join(path, file_name), engine = "pyogrio")
    data = data.to_crs(CRS)
    return data

def read_zonedata(path: str, file_name: str):
    # Check that paths are valid
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Directory {path} does not exist.")
    files = os.listdir(path)
    if file_name not in files:
        raise FileNotFoundError(f"File {file_name} not found. Available files: {files}")
    # Return data
    return pd.read_csv(os.path.join(path, file_name), 
                        sep="\t", decimal=".", skipinitialspace=True, 
                        dtype={"zone_id": int}).dropna()

class ScenarioData(object):
    def __init__(self, 
                 name: str, 
                 base_data_path: str, 
                 scenario_data_path: str,
                 result_data_path: str,
                 spatial_data_path: str
                 ):
        """Container for result data of single scenario, which 
        also enables export to geopackage file format.

        Args:
            name : Scenario name
            results_path : Path to scenario results.
            zones_path : Path to model-system zones (geopackage)
        """
        self.name = name
        self.scenario_data_path = scenario_data_path
        self.result_data_path = result_data_path
        self.zones = read_spatial(spatial_data_path, "zones.gpkg")
        self.basemap = read_spatial(spatial_data_path, "water_areas.gpkg")
        self.zone_ids = self.zones.zone_id
        self.aggregations = read_zonedata(base_data_path, "admin_regions.agg")

    def get_input_data(self, file_name, geometry = False):
        data = read_zonedata(self.scenario_data_path, file_name)
        if geometry:
            data = self.zones.merge(data, on='zone_id', how='left')
        return data.loc[data.zone_id.isin(self.zone_ids)]

    def get_result_data(self, file_name, geometry = False):
        data = read_zonedata(self.result_data_path, file_name)
        if geometry:
            data = self.zones.merge(data, on='zone_id', how='left')
        return data.loc[data.zone_id.isin(self.zone_ids)]

    def set_subregion(self, subregion_type: str, subregions: list):
        cols = list(self.aggregations.columns)
        if subregion_type not in list(cols):
            print(f"Subregion type not found. Available types: {cols}.")
        for subregion in subregions:
            if subregion not in self.aggregations[subregion_type].to_list():
                print(f"Subregion {subregion} not in zone aggregations.")
        self.zone_ids = self.aggregations.loc[self.aggregations[subregion_type].isin(subregions)]["zone_id"]        

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
    
    def costs_from(self, time_period, mtx_type, ass_class, origin_zone):
        matrix, lookup = self.read_costs(time_period, ass_class, mtx_type)
        return pd.DataFrame(cost = matrix[:,lookup == origin_zone], index=lookup)

        