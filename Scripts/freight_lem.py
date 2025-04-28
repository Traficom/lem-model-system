from argparse import ArgumentParser
import sys
from pathlib import Path
import numpy
import json
from pandas import DataFrame

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
    purposes = create_purposes(parameters_path / "domestic", 
                               [zonedata, resultdata, costdata["freight"]])
    purps_to_assign = list(filter(lambda purposes: purposes[0] in
                                  list(purposes), args.specify_commodity_names))
    
    ass_model.prepare_freight_network(costdata["car_cost"], purps_to_assign)
    impedance = ass_model.freight_network.assign()
    truck_distances = {key: impedance["dist"][key] for key in param.truck_classes}
    del impedance["cost"]
    impedance = {mode: {mtx_type: impedance[mtx_type][mode] for mtx_type in impedance
                        if mode in impedance[mtx_type]}
                        for mode in ("truck", "freight_train", "ship")}
    
    total_demand = {mode: numpy.zeros([len(zone_numbers), len(zone_numbers)])
                    for mode in param.truck_classes}
    for purpose in purposes.values():
        log.info(f"Calculating demand for domestic purpose: {purpose.name}")
        demand = purpose.calc_traffic(impedance)
        for mode in demand:
            ass_model.freight_network.set_matrix(mode, demand[mode])
            if purpose.name not in args.specify_commodity_names:
                continue
            with resultmatrices.open("freight_demand", "vrk", zone_numbers, m="a") as mtx:
                mtx[f"{purpose}_{mode}"] = demand[mode]
        if purpose.name in args.specify_commodity_names:
            ass_model.freight_network.save_network_volumes(purpose.name)
        ass_model.freight_network.output_traversal_matrix(set(demand), resultdata.path)
        demand["truck"] += transform_traversal_data(resultdata.path, zone_numbers)
        for mode in ("truck", "trailer_truck"):
            total_demand[mode] += purpose.calc_vehicles(demand["truck"], mode)
        write_purpose_summary(purpose.name, demand, impedance, resultdata)
        write_zone_summary(purpose.name, zone_numbers, demand, resultdata)
    write_vehicle_summary(total_demand, truck_distances, resultdata)
    resultdata.flush()
    
    purposes = create_purposes(parameters_path / "foreign",
                               [zonedata, resultdata, costdata["freight"]])
    for purpose in purposes.values():
        log.info(f"Calculating demand for foreign purpose: {purpose.name}")

    for ass_class in total_demand:
        ass_model.freight_network.set_matrix(ass_class, total_demand[ass_class])
    ass_model.freight_network._assign_trucks()
    log.info("Simulation ready.")

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
        args[-1] = args[-1][commodity_conversion[commodity]]
        purposes[commodity] = FreightPurpose(*args, parameters_path.stem)
    return purposes

def write_purpose_summary(purpose_name: str, demand: dict, impedance: dict, 
                          resultdata: ResultsData):
    """Write purpose-mode specific summary as txt-file containing mode shares 
    calculated from demand (tons), mode specific demand (tons), mode shares 
    calculated from mileage, and mode specific ton-mileage.
    """
    modes = list(demand)
    mode_tons = [numpy.sum(demand[mode])+0.01 for mode in modes]
    shares_tons = [tons / sum(mode_tons) for tons in mode_tons]
    mode_ton_dist = [numpy.sum(demand[mode]*impedance[mode]["dist"])+0.01 for mode in modes]
    shares_mileage = [share / sum(mode_ton_dist) for share in mode_ton_dist]
    df = DataFrame(data={
        "Commodity": [purpose_name]*len(modes),
        "Mode": modes,
        "Mode share from tons (%)": [round(i, 3) for i in shares_tons],
        "Tons (t/annual)": [int(i) for i in mode_tons],
        "Mode share from mileage (%)": [round(i, 3) for i in shares_mileage],
        "Ton mileage (tkm/annual)": [int(i) for i in mode_ton_dist]
        })
    filename = f"freight_purpose_summary.txt"
    resultdata.print_concat(df, filename)

def write_zone_summary(purpose_name: str, zone_numbers: list, 
                       demand: dict, resultdata: ResultsData):
    """Write purpose and mode specific departing and arriving tons for each zone
    in zone mapping.
    """
    df = DataFrame(index=zone_numbers)
    for mode in demand:
        df[f"Departing_{purpose_name}_{mode}"] = numpy.sum(demand[mode], axis=1, dtype="int32")
        df[f"Arriving_{purpose_name}_{mode}"] = numpy.sum(demand[mode], axis=0, dtype="int32")
    filename = f"freight_zone_summary.txt"
    resultdata.print_data(df, filename)

def write_vehicle_summary(demand: dict, dist: dict, resultdata: ResultsData):
    """Write summary for truck classes and their mileage."""
    modes = list(demand)
    vehicles_sum = [numpy.sum(demand[mode]) for mode in modes]
    mileage_sum = [numpy.sum(dist.pop(mode)*demand[mode]) for mode in modes]
    df = DataFrame(data={
        "Mode": modes,
        "Vehicle trips (day)": [int(i) for i in vehicles_sum],
        "Vehicle mileage (vkm/day)": [int(i) for i in mileage_sum]
        })
    filename = f"freight_vehicle_summary.txt"
    resultdata.print_data(df, filename)

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
