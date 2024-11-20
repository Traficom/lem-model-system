from argparse import ArgumentParser
import sys
from pathlib import Path
import numpy
import json
from typing import List

import utils.log as log
from datahandling.zonedata import FreightZoneData
from datahandling.resultdata import ResultsData
from assignment.emme_assignment import EmmeAssignmentModel
from assignment.emme_bindings.emme_project import EmmeProject
from datatypes.purpose import FreightPurpose
from datahandling.matrixdata import MatrixData

from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost
import parameters.assignment as param
from parameters.commodity import commodity_conversion

BASE_FOLDER = Path(__file__).parent
BASE_ZONEDATA_FILE = "freight_zonedata.gpkg"


def main(args):
    base_zonedata_path = Path(BASE_FOLDER, args.baseline_data_path, BASE_ZONEDATA_FILE)
    cost_data_path = Path(BASE_FOLDER, args.cost_data_path)
    results_path = Path(BASE_FOLDER, args.results_path)
    emme_project_path = Path(BASE_FOLDER, args.emme_path)
    parameters_path = BASE_FOLDER / "parameters" / "freight"
    
    ass_model = EmmeAssignmentModel(EmmeProject(emme_project_path),
                                    first_scenario_id=args.first_scenario_id,
                                    save_matrices=args.save_emme_matrices,
                                    first_matrix_id=args.first_matrix_id)
    zone_numbers = ass_model.zone_numbers
    zonedata = FreightZoneData(base_zonedata_path, zone_numbers, "koko_suomi")
    resultdata = ResultsData(results_path)
    resultmatrices = MatrixData(results_path / "Matrices" / "koko_suomi")
    costdata = json.loads(cost_data_path.read_text("utf-8"))
    purposes = {}
    for file in parameters_path.rglob("*.json"):
        commodity_params = json.loads(file.read_text("utf-8"))
        commodity = commodity_params["name"]
        if commodity not in ("marita", "kalevi"):
            continue
        purposes[commodity] = FreightPurpose(commodity_params, zonedata, resultdata)
    ass_model.prepare_freight_network(costdata["car_cost"], list(purposes))
    imps = ass_model.freight_network.assign()
    
    impedance = {
        "truck": {
            "dist": imps["dist"]["truck"],
            "time": imps["time"]["truck"],
            "toll": numpy.zeros([len(zone_numbers), len(zone_numbers)])
        },
        "freight_train": {
            "dist": imps["dist"]["freight_train"],
            "time": imps["time"]["freight_train"],
        },
        "ship": {
            "dist": imps["dist"]["ship"],
            "channel": numpy.zeros([len(zone_numbers), len(zone_numbers)])
        },
        "freight_train_aux": {
            "dist": imps["aux_dist"]["freight_train"],
            "time": imps["aux_time"]["freight_train"],
            "toll": numpy.zeros([len(zone_numbers), len(zone_numbers)])
        },
        "ship_aux": {
            "dist": imps["aux_dist"]["ship"],
            "time": imps["aux_time"]["ship"],
            "toll": numpy.zeros([len(zone_numbers), len(zone_numbers)])
        }
    }
    for purpose_key, purpose_value in purposes.items():
        commodity_costs = costdata["freight"][commodity_conversion[purpose_key]]
        costs = {"truck": {}, "freight_train": {}, "ship": {}}
        costs["truck"]["cost"] = calc_road_cost(commodity_costs,
                                                impedance["truck"])
        costs["freight_train"]["cost"] = calc_rail_cost(commodity_costs,
                                                        impedance["freight_train"],
                                                        impedance["freight_train_aux"])
        costs["ship"]["cost"] = calc_ship_cost(commodity_costs,
                                               impedance["ship"],
                                               impedance["ship_aux"])
        demand = purpose_value.calc_traffic(costs, purpose_key)
    log.info("Simulation ended.")


if __name__ == "__main__":
    parser = ArgumentParser(epilog="Freight lem-model-system entry point script.")
    config = {
        "BASELINE_DATA_PATH": "tests/test_data/Scenario_input_data/2030_test/",
        "COST_DATA_PATH": "tests/test_data/Scenario_input_data/2030_test/costdata.json",
        "RESULTS_PATH": "tests/test_data/Results/test/",
        "EMME_PATH": "tests/test_data/Results/test_assignment/test_assignment.emp",
        "FIRST_SCENARIO_ID": 19,
        "SAVE_EMME_MATRICES": True,
        "FIRST_MATRIX_ID": 200,
        "SPECIFY_COMMODITY_NAMES": ["marita"]
    }
    parser.add_argument(
        "--baseline-data-path",
        type=str,
        help="Path to folder containing both baseline zonedata and -matrices (Given privately by project manager)"),
    parser.add_argument(
        "--cost-data-path",
        type=str,
        help="Path to file containing transport cost data"),
    parser.add_argument(
        "--results-path",
        type=str,
        help="Path to folder where result data is saved to."),
    parser.add_argument(
        "--emme-path",
        type=str,
        help="Filepath to .emp EMME-project-file"),
    parser.add_argument(
        "--first-scenario-id",
        type=int,
        help="First (biking) scenario ID within EMME project (.emp)."),
    parser.add_argument(
        "--save-emme-matrices",
        type=bool,
        help="Using this flag saves matrices for specified commodities."),
    parser.add_argument(
        "--first-matrix-id",
        type=int,
        help="First matrix ID within EMME project (.emp)."),
    parser.add_argument(
        "--specify-commodity-names",
        type=List[str],
        help="Commodity names to be assigned and saved."),

    parser.set_defaults(
        **{key.lower(): val for key, val in config.items()})
    args = parser.parse_args()
    
    if not isinstance(args.specify_commodity_names, list):
        raise TypeError("Invalid type for save commodity names")
    for name in args.specify_commodity_names:
        if name not in list(commodity_conversion):
            raise ValueError("Invalid given commodity name.")
    if len(args.specify_commodity_names) == 0:
        args.save_emme_matrices = False
    
    if sys.version_info.major == 3:
        main(args)
    else:
        log.error("Python version not supported, must use version 3")
