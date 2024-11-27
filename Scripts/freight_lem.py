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

from datahandling.traversaldata import transform_traversal_data
from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost
from parameters.commodity import commodity_conversion

BASE_FOLDER = Path(__file__).parent
BASE_ZONEDATA_FILE = "freight_zonedata.gpkg"


def main(args):
    log.info("Starting simulation.")
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
    purps_to_assign = list(filter(lambda purposes: purposes[0] in
                                  list(purposes), args.specify_commodity_names))
    ass_model.prepare_freight_network(costdata["car_cost"], purps_to_assign)
    impedance = ass_model.freight_network.assign()
    zeros = numpy.zeros([len(zone_numbers), len(zone_numbers)])
    impedance = {
        "truck": {
            "dist": impedance["dist"]["truck"],
            "time": impedance["time"]["truck"],
            "toll": zeros
        },
        "freight_train": {
            "dist": impedance["dist"]["freight_train"],
            "time": impedance["time"]["freight_train"],
        },
        "ship": {
            "dist": impedance["dist"]["ship"],
            "channel": zeros
        },
        "freight_train_aux": {
            "dist": impedance["aux_dist"]["freight_train"],
            "time": impedance["aux_time"]["freight_train"],
            "toll": zeros
        },
        "ship_aux": {
            "dist": impedance["aux_dist"]["ship"],
            "time": impedance["aux_time"]["ship"],
            "toll": zeros
        }
    }
    matrix_counter = args.first_matrix_id
    for purpose, purpose_value in purposes.items():
        log.info(f"Launching calculations for purpose: {purpose}")
        commodity_costs = costdata["freight"][commodity_conversion[purpose]]
        costs = {"truck": {}, "freight_train": {}, "ship": {}}
        costs["truck"]["cost"] = calc_road_cost(commodity_costs,
                                                impedance["truck"])
        costs["freight_train"]["cost"] = calc_rail_cost(commodity_costs,
                                                        impedance["freight_train"],
                                                        impedance["freight_train_aux"])
        costs["ship"]["cost"] = calc_ship_cost(commodity_costs,
                                               impedance["ship"],
                                               impedance["ship_aux"])
        demand = purpose_value.calc_traffic(costs, purpose)
        for mode in demand:
            ass_model.freight_network.set_matrix(mode, demand[mode])
            if purpose not in args.specify_commodity_names:
                continue
            # Explicitly save commodity
            matrix_id = f"mf{matrix_counter}"
            matrix_name = f"{purpose}_{mode}"
            matrix_type = "demand"
            ass_model._create_matrix(matrix_id, matrix_name, matrix_type, overwrite=True)
            matrix_counter += 1
            ass_model.freight_network.emme_matrices.update(
                {matrix_name: {matrix_type: matrix_id}})
            ass_model.freight_network.set_matrix(matrix_name, demand[mode])
            with resultmatrices.open("freight_demand", "vrk", zone_numbers, m="a") as mtx:
                mtx[matrix_name] = demand[mode]
        if purpose in args.specify_commodity_names:
            ass_model.freight_network.save_network_volumes(purpose)
            matrix_counter += 7 # Shift to next 10 digit
        ass_model.freight_network.output_traversal_matrix(resultdata.path)
        aux_demand = transform_traversal_data(resultdata.path, zone_numbers)
    log.info("Simulation ready.")

if __name__ == "__main__":
    parser = ArgumentParser(epilog="Freight lem-model-system entry point script.")
    config = {
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "TEXT",
        "SCENARIO_NAME": "test",
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
        "--log-level",
        choices={"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
    )
    parser.add_argument(
        "--log-format",
        choices={"TEXT", "JSON"},
    )
    
    parser.add_argument(
        "--scenario-name",
        type=str,
        help="Scenario name"),
    parser.add_argument(
        "--baseline-data-path",
        type=str,
        help="Path to folder containing both baseline zonedata and -matrices"),
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
        help="Commodity names in 29 classification. Assigned and saved as mtx. Currently max 3."),

    parser.set_defaults(
        **{key.lower(): val for key, val in config.items()})
    args = parser.parse_args()
    
    if not isinstance(args.specify_commodity_names, list):
        raise TypeError("Invalid type for save commodity names")
    for name in args.specify_commodity_names:
        if name not in list(commodity_conversion):
            raise ValueError("Invalid given commodity name.")
    if len(args.specify_commodity_names) > 3:
        raise ValueError("Maximum of 3 commodities can be specified.")
    if len(args.specify_commodity_names) == 0:
        args.save_emme_matrices = False
    
    log.initialize(args)
    if sys.version_info.major == 3:
        main(args)
    else:
        log.error("Python version not supported, must use version 3")
