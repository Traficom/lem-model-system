from argparse import ArgumentParser
import os
import sys
from pathlib import Path
import numpy
from typing import List, Dict, Union

import utils.config
import utils.log as log
from utils.validate_network import validate
from assignment.mock_assignment import MockAssignmentModel
from datahandling.matrixdata import MatrixData
from datahandling.zonedata import ZoneData
import parameters.assignment as param
from lem import BASE_ZONEDATA_DIR


def main(args):
    base_zonedata_path = Path(args.baseline_data_path, BASE_ZONEDATA_DIR)
    emme_paths: Union[str,List[str]] = args.emme_paths
    first_scenario_ids: Union[int,List[int]] = args.first_scenario_ids
    forecast_zonedata_paths: Union[str,List[str]] = args.forecast_data_paths

    if not emme_paths:
        msg = "Missing required argument 'emme-paths'."
        log.error(msg)
        raise ValueError(msg)
    if not first_scenario_ids:
        msg = "Missing required argument 'first-scenario-ids'."
        log.error(msg)
        raise ValueError(msg)
    if not forecast_zonedata_paths:
        msg = "Missing required argument 'forecast-zonedata-paths'."
        log.error(msg)
        raise ValueError(msg)
    # Check arg lengths
    if not (len(emme_paths) == len(first_scenario_ids)):
        msg = ("Non-matching number of emme-paths (.emp files) "
               + "vs. number of first-scenario-ids")
        log.error(msg)
        raise ValueError(msg)
    if not (len(emme_paths) == len(forecast_zonedata_paths)):
        msg = ("Non-matching number of emme-paths (.emp files) "
               + "vs. number of forecast-zonedata-paths")
        log.error(msg)
        raise ValueError(msg)

    # Check basedata input
    log.info("Checking base inputdata...")
    # Check filepaths (& first .emp path for zone_numbers in base zonedata)
    if not base_zonedata_path.exists():
        msg = "Baseline zonedata directory '{}' does not exist.".format(
            base_zonedata_path)
        log.error(msg)
        raise ValueError(msg)

    zone_numbers: Dict[str, numpy.array] = {}
    calculate_long_dist_demand = args.long_dist_demand_forecast == "calc"
    time_periods = (["vrk"] if calculate_long_dist_demand
        else param.time_periods)

    # Check scenario based input data
    log.info("Checking base zonedata & scenario-based input data...")
    for i, emp_path in enumerate(emme_paths):
        log.info("Checking input data for scenario #{} ...".format(i))

        # Check network
        if args.do_not_use_emme:
            mock_result_path = Path(
                args.results_path, args.scenario_name, "Matrices",
                args.submodel[i])
            if not mock_result_path.exists():
                msg = "Mock Results directory {} does not exist.".format(
                    mock_result_path)
                log.error(msg)
                raise NameError(msg)
            assignment_model = MockAssignmentModel(
                MatrixData(mock_result_path), time_periods=time_periods)
            zone_numbers[args.submodel[i]] = assignment_model.zone_numbers
        else:
            if not os.path.isfile(emp_path):
                msg = ".emp project file not found in given '{}' location.".format(
                    emp_path)
                log.error(msg)
                raise ValueError(msg)
            import inro.emme.desktop.app as _app # type: ignore
            app = _app.start_dedicated(
                project=emp_path, visible=False, user_initials="HSL")
            emmebank = app.data_explorer().active_database().core_emmebank
            scen = emmebank.scenario(first_scenario_ids[i])
            zone_numbers[args.submodel[i]] = scen.zone_numbers
            if scen is None:
                msg = "Project {} has no scenario {}".format(
                    emp_path, first_scenario_ids[i])
                log.error(msg)
                raise ValueError(msg)
            for scenario in emmebank.scenarios():
                if scenario.zone_numbers != scen.zone_numbers:
                    log.warn("Scenarios with different zones found in EMME bank!")
            attrs = {
                "NODE": ["#transit_stop_b", "#transit_stop_e", "#transit_stop_g",
                         "#transit_stop_t", "#transit_stop_p"],
                "LINK": ["#buslane"],
                "TRANSIT_LINE": ["#keep_stops"],
            }
            for tp in time_periods:
                attrs["LINK"].append(f"#car_time_{tp}")
                attrs["TRANSIT_LINE"].append(f"#hdw_{tp}")
            for obj_type in attrs:
                for attr in attrs[obj_type]:
                    if scen.network_field(obj_type, attr) is None:
                        msg = "Network field {} missing from scenario {}".format(
                            attr, scen.id)
                        log.error(msg)
                        raise ValueError(msg)
            # TODO Count existing extra attributes which are NOT included
            # in the set of attributes created during model run
            nr_transit_classes = len(param.transit_classes)
            nr_segment_results = len(param.segment_results)
            nr_veh_classes = len(param.emme_matrices)
            nr_assignment_modes = len(param.assignment_modes)
            nr_new_attr = {
                "nodes": nr_transit_classes * (nr_segment_results-1),
                "links": nr_veh_classes + len(param.park_and_ride_classes) + 1,
                "transit_lines": nr_transit_classes + 2,
                "transit_segments": nr_transit_classes*nr_segment_results + 2,
            }
            link_costs_defined = False
            for tp in time_periods:
                if scen.network_field("LINK", f"#hinta_{tp}") is not None:
                    link_costs_defined = True
            if link_costs_defined:
                nr_new_attr["links"] += nr_assignment_modes + 1
            if not args.separate_emme_scenarios:
                # If results from all time periods are stored in same
                # EMME scenario
                for key in nr_new_attr:
                    nr_new_attr[key] *= len(time_periods) + 1
            # Attributes created during congested transit assignment
            nr_new_attr["transit_segments"] += 3
            dim = emmebank.dimensions
            dim["nodes"] = dim["centroids"] + dim["regular_nodes"]
            attr_space = 0
            for key in nr_new_attr:
                attr_space += dim[key] * nr_new_attr[key]
            if dim["extra_attribute_values"] < attr_space:
                msg = "At least {} words required for extra attributes".format(
                    attr_space)
                log.error(msg)
                raise ValueError(msg)
            validate(scen.get_network(), time_periods)
            app.close()

    for submodel in zone_numbers:
        # Check base matrices
        base_matrices_path = Path(
            args.baseline_data_path, "Matrices", submodel)
        if not base_matrices_path.exists():
            msg = "Baseline matrices' directory '{}' does not exist.".format(
                base_matrices_path)
            log.error(msg)
            raise ValueError(msg)
        if not calculate_long_dist_demand:
            matrixdata = MatrixData(base_matrices_path)
            for tp in time_periods:
                with matrixdata.open("demand", tp, zone_numbers[submodel]) as mtx:
                    for ass_class in param.transport_classes:
                        a = mtx[ass_class]

    for data_path, submodel in zip(forecast_zonedata_paths, args.submodel):
        # Check forecasted zonedata
        if not os.path.exists(data_path):
            msg = "Forecast data directory '{}' does not exist.".format(
                data_path)
            log.error(msg)
            raise ValueError(msg)
        forecast_zonedata = ZoneData(
            Path(data_path), zone_numbers[submodel], submodel)

    log.info("Successfully validated all input files")


if __name__ == "__main__":
    # Initially read defaults from config file ("dev-config.json")
    # but allow override via command-line arguments
    config = utils.config.read_from_file()
    parser = ArgumentParser(epilog="HELMET model system entry point script.")
    # Logging
    parser.add_argument(
        "--log-level",
        choices={"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
    )
    parser.add_argument(
        "--log-format",
        choices={"TEXT", "JSON"},
    )
    parser.add_argument(
        "-f", "--long-dist-demand-forecast",
        type=str,
        help=("If 'calc', runs assigment with free-flow speed and "
              + "calculates demand for long-distance trips. "
              + "If 'base', takes long-distance trips from base matrices. "
              + "If path, takes long-distance trips from that path.")
    )
    parser.add_argument(
        "--do-not-use-emme",
        action="store_true",
        help="Using this flag runs with MockAssignmentModel instead of EmmeAssignmentModel, not requiring EMME.",
    )
    parser.add_argument(
        "-s", "--separate-emme-scenarios",
        action="store_true",
        help="Using this flag creates four new EMME scenarios and saves network time-period specific results in them.",
    )
    parser.add_argument(
        "--scenario-name",
        type=str,
        help="Name of HELMET scenario. Influences result folder name and log file name."),
    parser.add_argument(
        "--results-path",
        type=str,
        help="Path to folder where result data is saved to."),
    # Base input (across all scenarios)
    parser.add_argument(
        "--baseline-data-path",
        type=str,
        help="Path to folder containing both baseline zonedata and -matrices (Given privately by project manager)"),
    # Scenarios' individual input
    parser.add_argument(
        "--submodel",
        type=str,
        nargs="+",
        required=True,
        help="Name of submodel, used for choosing appropriate zone mapping"),
    parser.add_argument(
        "--emme-paths",
        type=str,
        nargs="+",
        required=True,
        help="List of filepaths to .emp EMME-project-files"),
    parser.add_argument(
        "--first-scenario-ids",
        type=int,
        nargs="+",
        required=True,
        help="List of first (biking) scenario IDs within EMME project (.emp)."),
    parser.add_argument(
        "--forecast-data-paths",
        type=str,
        nargs="+",
        required=True,
        help="List of paths to folder containing forecast zonedata"),
    parser.set_defaults(
        **{key.lower(): val for key, val in config.items()})
    args = parser.parse_args()

    log.initialize(args)
    log.debug(utils.config.dump(vars(args)))

    if sys.version_info.major == 3:
        main(args)
    else:
        log.error("Python version not supported, must use version 3")
