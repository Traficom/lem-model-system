import json
from pathlib import Path

import utils.log as log
from datatypes.purpose import FreightPurpose
from parameters.commodity import commodity_conversion
    

def create_purposes(parameters_path: Path, purpose_args: list) -> dict:
    """Creates instances of FreightPurpose class for each model parameter json file
    in parameters path.

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
            purposes[commodity] = FreightPurpose(*args)
        except KeyError:
            log.warn(f"Aggregated commodity class '{commodity_conversion[commodity]}' "
                      f"for commodity {commodity} not found in costs json.")
    return purposes
