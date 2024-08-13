
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datahandling.matrixdata import MatrixData

CRS = "EPSG:3067"
def read_spatial(file_path: Path, layer_name: str) -> gpd.GeoDataFrame:
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")
    data = gpd.read_file(file_path, layer = layer_name, engine = "pyogrio")
    data = data.to_crs(CRS)
    return data

def read_zonedata(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist.")
    return pd.read_csv(file_path, delim_whitespace=True, comment='#',
                       decimal=".", skipinitialspace=True, dtype={"zone_id": int})

def read_mtx(file_path: Path, time_period: str, mtx_type: str, ass_class: str):
    """
    Read cost matrix from omx files.

    Args:
        time_period (str) : Time period
        mtx_type (str) : Matrix type
        ass_class (str) : Assignment class of model

    Return
        numpy.Matrix : Cost matrix of specified type 
        pandas.Series : Zone mapping
    """
    matrixdata = MatrixData(file_path)
    with matrixdata.open(mtx_type, time_period) as mtx:
        matrix = mtx[ass_class]
        lookup = mtx.zone_numbers
    return matrix, lookup


class ScenarioData(object):
    def __init__(self, 
                 scenario_name: str, 
                 submodel: str,
                 base_data_path: str, 
                 result_data_path: str,
                 spatial_data_path: str
                 ):
        """Container for result data of single scenario.

        Args:
            name : Scenario name
            submodel : Submodel name
            results_path : Path to scenario results.
            zones_path : Path to model-system zones (geopackage)
        """
        self.name = scenario_name
        self.submodel = submodel
        # Spatial
        self.spatial_data_path = Path(spatial_data_path)
        self.zones = read_spatial(self.spatial_data_path / "zones.gpkg", "zones")
        # Baseline
        base_data_path = Path(base_data_path)
        self.zone_ids = self.zones.zone_id
        self.aggregations = read_zonedata(base_data_path / "aggregations.agg")
        # Scenario specific
        self.result_data_path = Path(result_data_path)
        if not self.result_data_path.is_dir():
            raise FileNotFoundError(f"Directory {self.result_data_path} does not exist.")
    
    def get_basemap_layer(self, layer_name: str):
        """Return layer from basemap Geopackage.

        Args:
            layer_name (str) : Name of layer (water/..)

        Returns:
            geopandas.GeoSeries: Geometry
        """
        return read_spatial(self.spatial_data_path / "basemap.gpkg", layer_name)

    def get_zonedata(self, file_path, geometry):
        data = read_zonedata(file_path)
        data = data.loc[data.zone_id.isin(self.zone_ids)]
        if geometry:
            return self.zones.merge(data, on='zone_id', how='inner')
        else:
            return data

    def get_input_data(self, file_name, geometry = False):
        return self.get_zonedata(self.result_data_path / self.name / file_name, geometry)

    def get_result_data(self, file_name, geometry = False):
        return self.get_zonedata(self.result_data_path / file_name, geometry)

    def set_subregion(self, type: str, subregions: list):
        try:
            column = self.aggregations[type]
        except:
            cols = list(self.aggregations.columns)
            raise KeyError(f"Subregion type not found. Available types: {cols}.")
        for subregion in subregions:
            if subregion not in column.to_list():
                print(f"Subregion {subregion} not in aggregations file.")
        self.zone_ids = self.aggregations.loc[column.isin(subregions)]["zone_id"]        

    def costs_from(self, time_period, mtx_type, ass_class, zone_id, geometry = False):
        """
        Get costs from zone to all other zones.

        Args:
            time_period (str) : Time period
            mtx_type (str) : Matrix type
            ass_class (str) : Assignment class of model
            zone_id (int) : Zone id for origin zone
        
        Return
            pandas.Series : Cost vector from zone to all other zones
        """
        matrix, lookup = read_mtx(Path(self.result_data_path, "Matrices", self.submodel), 
                                  time_period, mtx_type, ass_class)
        data = pd.DataFrame({"zone_id": lookup, "cost":  matrix[:,lookup.index(zone_id)]}, index=lookup)
        if geometry:
            data = self.zones.merge(data, on='zone_id', how='left')
        return data.loc[data.zone_id.isin(self.zone_ids)]

        