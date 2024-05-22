
import pandas as pd
import geopandas as gpd
import os

CRS = "EPSG:3067"

def read_zone_data(filepath: str) -> pd.DataFrame:
    """Reads model-system result data.

    Args:
        filepath (str): Path to the file to read
    
    Returns:
        pd.DataFrame: A pandas DataFrame containing the results data.
    """
    return pd.read_csv(
        filepath, sep="\t", decimal=".", skipinitialspace=True,
        dtype={"zone_id": int}).dropna()

def read_zones(data_path: str) -> gpd.GeoDataFrame:
    zones = gpd.read_file(os.path.join(data_path, "zones.gpkg"), engine = "pyogrio")
    zones = zones.to_crs(CRS)
    return zones
