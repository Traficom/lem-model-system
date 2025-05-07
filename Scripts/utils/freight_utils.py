import json
import log
from typing import TYPE_CHECKING

from datatypes.purpose import FreightPurpose
from parameters.commodity import commodity_conversion

if TYPE_CHECKING:
    from pathlib import Path
    

def create_purposes(parameters_path: Path, purpose_args: list):
    """Creates instances of FreightPurpose class for each model parameter json file
    in parameters path. Include information whether estimated model type is
    either 'domestic' or 'foreign'.
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