from argparse import ArgumentParser
import sys
from pathlib import Path
import numpy
import json

import utils.log as log
import utils.config
import parameters.assignment as param
from datahandling.zonedata import FreightZoneData
from datahandling.resultdata import ResultsData
from assignment.emme_assignment import EmmeAssignmentModel
from assignment.emme_bindings.emme_project import EmmeProject
from datatypes.purpose import FreightPurpose
from datahandling.matrixdata import MatrixData

from datahandling.traversaldata import transform_traversal_data
from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost
from parameters.commodity import commodity_conversion

BASE_ZONEDATA_FILE = "freight_zonedata.gpkg"


def main(args):
    base_zonedata_path = Path(args.baseline_data_path, BASE_ZONEDATA_FILE)
    cost_data_path = Path(args.cost_data_path)
    results_path = Path(args.results_path, args.scenario_name)
    emme_project_path = Path(args.emme_path)
    parameters_path = Path(__file__).parent / "parameters" / "freight"
    
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
        purposes[commodity] = FreightPurpose(commodity_params,
                                             zonedata,
                                             resultdata,
                                             costdata["freight"][commodity_conversion[commodity]])
    purps_to_assign = list(filter(lambda purposes: purposes[0] in
                                  list(purposes), args.specify_commodity_names))
    
    ass_model.prepare_freight_network(costdata["car_cost"], purps_to_assign)
    impedance = ass_model.freight_network.assign()
    del impedance["cost"]
    impedance = {mode: {mtx_type: impedance[mtx_type][mode] for mtx_type in impedance
                        if mode in impedance[mtx_type]}
                        for mode in ("truck", "freight_train", "ship")}
    
    total_demand = {mode: numpy.zeros([len(zone_numbers), len(zone_numbers)])
                    for mode in param.truck_classes}
    for purpose in purposes.values():
        log.info(f"Calculating demand for purpose: {purpose.name}")
        demand = purpose.calc_traffic(impedance)
        for mode in demand:
            ass_model.freight_network.set_matrix(mode, demand[mode])
            if purpose.name not in args.specify_commodity_names:
                continue
            with resultmatrices.open("freight_demand", "vrk", zone_numbers, m="a") as mtx:
                mtx[f"{purpose}_{mode}"] = demand[mode]
        if purpose.name in args.specify_commodity_names:
            ass_model.freight_network.save_network_volumes(purpose.name)
        ass_model.freight_network.output_traversal_matrix(resultdata.path)
        demand["truck"] += transform_traversal_data(resultdata.path, zone_numbers)
        for mode in ("truck", "trailer_truck"):
            total_demand[mode] += purpose.calc_vehicles(demand["truck"], mode)
    for ass_class in total_demand:
        ass_model.freight_network.set_matrix(ass_class, total_demand[ass_class])
    ass_model.freight_network._assign_trucks()
    log.info("Simulation ready.")

if __name__ == "__main__":
    parser = ArgumentParser(epilog="Freight lem-model-system entry point script.")
    config = utils.config.read_from_file()
    
    parser.add_argument(
        "--log-level",
        choices={"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
    parser.add_argument(
        "--log-format",
        choices={"TEXT", "JSON"})
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
        nargs="*",
        choices=commodity_conversion,
        help="Commodity names in 29 classification. Assigned and saved as mtx."),

    parser.set_defaults(
        **{key.lower(): val for key, val in config.items()})
    args = parser.parse_args()
    log.initialize(args)
    if sys.version_info.major == 3:
        main(args)
    else:
        log.error("Python version not supported, must use version 3")
