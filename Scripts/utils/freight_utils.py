import json
import numpy
from pathlib import Path
from typing import Dict

import utils.log as log
from datatypes.purpose import FreightPurpose
from datahandling.zonedata import FreightZoneData
from datahandling.resultdata import ResultsData
from parameters.commodity import commodity_conversion
from datahandling.matrixdata import MatrixData
from assignment.freight_assignment import FreightAssignmentPeriod
    

def create_purposes(parameters_path: Path, zonedata: FreightZoneData, 
                    resultdata: ResultsData, costdata: Dict[str, dict]) -> dict:
    """Creates instances of FreightPurpose class for each model parameter json file
    in parameters path.

    Parameters
    ----------
    parameters_path : Path
        Path object to estimation model type folder containing model parameter
        json files
    zonedata : FreightZoneData
        freight zonedata container
    resultdata : ResultsData
        handler for result saving operations 
    costdata : Dict[str, dict]
        Freight purpose : Freight mode
            Freight mode (truck/freight_train/ship) : mode
                Mode (truck/trailer_truck...) : unit cost name
                    unit cost name : unit cost value

    Returns
    -------
    dict[str, FreightPurpose]
        purpose name : FreightPurpose
    """
    purposes = {}
    for file in parameters_path.rglob("*.json"):
        commodity_params = json.loads(file.read_text("utf-8"))
        commodity = commodity_params["name"]
        try:
            purpose_cost = costdata[commodity_conversion[commodity]]
            purposes[commodity] = FreightPurpose(commodity_params, zonedata, 
                                                 resultdata, purpose_cost)
        except KeyError:
            log.warn(f"Aggregated commodity class '{commodity_conversion[commodity]}' "
                      f"for commodity {commodity} not found in costs json.")
    return purposes

def store_demand(freight_network: FreightAssignmentPeriod, resultmatrices: MatrixData, 
                 all_zones: numpy.ndarray, zones: numpy.ndarray, 
                 mode: str, demand: numpy.ndarray, 
                 save_demand: bool, omx_filename: str, key_prefix: str = ""):
    """Handle storing demand matrices by assessing dimensions compatibility with
    Emme network and whether demand should be saved on drive. 

    Parameters
    ----------
    freight_network : FreightAssignmentPeriod
        freight assignment period object
    resultmatrices : MatrixData
        handle for I/O matrix data handling
    all_zones : numpy.ndarray
        all zones in Emme network
    zones : numpy.ndarray
        zones within peripheral bounds of Emme network
    mode : str
        freight mode/assignment class
    demand : numpy.ndarray
        matrix that is set to Emme
    save_demand : bool
        if demand matrix should be saved
    omx_filename : str
        name of an external .omx file for saving results
    key_prefix : str, by default empty string
        optional name prefix for matrix e.g. purpose name
    """
    emme_mtx = assess_demand_dimensions(demand, all_zones.size, zones.size)
    freight_network.set_matrix(mode, emme_mtx)
    if save_demand:
        with resultmatrices.open(omx_filename, freight_network.name, 
                                 all_zones, m="a") as mtx:
            keyname = f"{key_prefix}_{mode}_" if key_prefix else mode
            mtx[keyname] = emme_mtx

def assess_demand_dimensions(demand: numpy.ndarray, nr_all_zones: int, 
                             nr_zones: int) -> numpy.ndarray:
    """Evaluates whether given demand matrix needs to be padded with zones 
    to maintain zone compatibility with scenario's Emme network.

    Parameters
    ----------
    demand : numpy.ndarray
        type demand matrix which is assessed before setting into Emme
    nr_all_zones : int
        size all zones in Emme network
    nr_zones : int
        size of zones within peripheral bounds in Zonedata

    Returns
    -------
    numpy.ndarray
        demand with/without zone padding
    """
    fill_mtx = demand
    if demand.size != nr_all_zones**2:
        fill_mtx = numpy.zeros([nr_all_zones, nr_all_zones], dtype=numpy.float32)
        fill_mtx[:nr_zones, :nr_zones] = demand
    return fill_mtx