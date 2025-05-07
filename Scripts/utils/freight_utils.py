import json
import numpy
from pathlib import Path

import utils.log as log
from datatypes.purpose import FreightPurpose
from parameters.commodity import commodity_conversion
    

def create_purposes(parameters_path: Path, purpose_args: list) -> dict:
    """Creates instances of FreightPurpose class for each model parameter json file
    in parameters path. Include information whether estimated model type is
    either 'domestic' or 'foreign'.

    Parameters
    ----------
    parameters_path : Path
        Path object to estimation model type folder containing model parameter
        json files
    purpose_args : list[Zonedata, ResultsData, dict]
        arguments to init FreightPurpose class containing instance of Zonedata,
        ResultsData and costs unit dictionary

    Returns
    -------
    dict[str, FreightPurpose]
        purpose name : FreightPurpose
    """
    purposes = {}
    for file in parameters_path.rglob("*.json"):
        args = purpose_args.copy()
        commodity_params = json.loads(file.read_text("utf-8"))
        commodity = commodity_params["name"]
        args.insert(0, commodity_params)
        try:
            args[-1] = args[-1][commodity_conversion[commodity]]
            purposes[commodity] = FreightPurpose(*args, parameters_path.stem)
        except KeyError:
            log.warn(f"Aggregated commodity class '{commodity_conversion[commodity]}' "
                      f"for commodity {commodity} not found in costs json.")
    return purposes

def assess_demand_dimensions(nr_all_zones: int, nr_zones: int, 
                             demand: numpy.ndarray) -> numpy.ndarray:
    """Evaluates whether given demand matrix needs to be padded with zones 
    to maintain zone compatibility with scenario's Emme network.

    Parameters
    ----------
    nr_all_zones : int
        number of all zones in Emme network
    nr_zones : int
        number of zones within peripheral bounds in Zonedata
    demand : numpy.ndarray
        Type demand or other matrix type which is assessed before setting into Emme

    Returns
    -------
    numpy.ndarray
        demand with/without zone padding
    """
    if demand.size == nr_all_zones**2:
        return demand
    fill_mtx = numpy.zeros([nr_all_zones, nr_all_zones], dtype=numpy.float32)
    fill_mtx[:nr_zones, :nr_zones] = demand
    return fill_mtx