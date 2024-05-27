
import os
import pandas as pd
import geopandas as gpd
from typing import Optional

from datahandling.matrixdata import MatrixData

def read_zone_data(filepath: str) -> pd.DataFrame:
    return pd.read_csv(
        filepath, sep="\t", decimal=".", skipinitialspace=True,
        dtype={"zone_id": int}).dropna()

CRS = "EPSG:3067"
def read_zones(data_path: str) -> gpd.GeoDataFrame:
    zones = gpd.read_file(os.path.join(data_path, "zones.gpkg"), engine = "pyogrio")
    zones = zones.to_crs(CRS)
    return zones

class ScenarioData(object):
    def __init__(self, 
                 name: str, 
                 base_data_path: str, 
                 scenario_data_path: str,
                 result_data_path: str
                 ):
        """Container for result data of single scenario, which 
        also enables export to geopackage file format.

        Args:
            name : Scenario name
            results_path : Path to scenario results.
            zones_path : Path to model-system zones (geopackage)
        """
        name = name
        paths = [base_data_path, scenario_data_path, result_data_path]
        for path in paths:
            if os.path.isdir(path):
                pass
            else:
                raise FileNotFoundError(f"Directory {path} does not exist.")
        self.base_data_path = base_data_path
        self.scenario_data_path = scenario_data_path
        self.result_data_path = result_data_path
        # Zonedata
        self.aggregations = read_zone_data(
            os.path.join(self.base_data_path, "admin_regions.agg"))
        # Spatial data
        self.zones = read_zones(base_data_path)            

    def set_subregion(self, subregion_type: str, subregions: list):
        data_columns = list(self.aggregations.columns)
        if subregion_type not in list(data_columns):
            print(f"Subregion type not found from aggregations. Available types: {data_columns}.")
        for subregion in subregions:
            if subregion not in self.aggregations[subregion_type].to_list():
                print(f"Subregion {subregion} not in zone aggregations.")
        ids = self.aggregations.loc[self.aggregations[subregion_type].isin(subregions)]["zone_id"]
        self.zones.loc[self.zones.zone_id.isin(ids)]
    
    def get_spatial_zonedata(self, name_zonedata: str):
        files = os.listdir(self.result_data_path)
        filename = f"{name_zonedata}.txt"
        if filename in files:
            zonedata = read_zone_data(os.path.join(self.result_data_path, filename))
        else:
            raise FileNotFoundError(f"File {filename} not found. Available files: {files}")
        return self.zones.merge(zonedata, on='zone_id', how='left')

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

        