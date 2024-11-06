from argparse import ArgumentParser
from pathlib import Path

import utils.config
import utils.log as log
from assignment.emme_bindings.emme_project import EmmeProject
import inro.emme.desktop.app as _app
import inro.emme.database.emmebank as _eb
import parameters.assignment as param

def create_emme_project(args):
    project_dir = args.emme_path
    project_name = args.project_name
    db_dir = Path(project_dir, project_name, "Database")
    project_path = _app.create_project(project_dir, project_name)
    db_dir.mkdir(parents=True, exist_ok=True)
    default_dimensions = {
        "scalar_matrices": 100,
        "origin_matrices": 100,
        "destination_matrices": 100,
        "full_matrices": 9999,
        "scenarios": args.number_of_emme_scenarios,
        "turn_entries": 100,
        "transit_vehicles": 40,
        "functions": 99,
        "operators": 5000,
        "sola_analyses": 240,
    }
    submodel_dimensions = {
        "alueelliset_osamallit": {
            "centroids": 3300,
            "regular_nodes": 45000,
            "links": 150000,
            "transit_lines": 3300,
            "transit_segments": 300000,
        },
        "koko_suomi": {
            "centroids": 10000,
            "regular_nodes": 120000,
            "links": 350000,
            "transit_lines": 8000,
            "transit_segments": 700000,
        },
        "koko_suomi_kunta": {
            "centroids": 320,
            "regular_nodes": 50000,
            "links": 130000,
            "transit_lines": 8000,
            "transit_segments": 500000,
        }
    }
    nr_transit_classes = len(param.transit_classes)
    nr_segment_results = len(param.segment_results)
    nr_veh_classes = len(param.emme_matrices)
    nr_attr = {
        "centroids": nr_transit_classes * (nr_segment_results-1),
        "regular_nodes": nr_transit_classes * (nr_segment_results-1),
        "links": nr_veh_classes + len(param.mixed_mode_classes) + 1,
        "transit_lines": nr_transit_classes + 2,
        "transit_segments": nr_transit_classes*nr_segment_results + 2,
    }
    
    if not args.separate_emme_scenarios:
    # If results from all time periods are stored in same
    # EMME scenario
        for key in nr_attr:
            nr_attr[key] *= len(param.time_periods) + 1

    # calculate extra attribute dimensions:
    dim = submodel_dimensions[args.submodel]
    dim["extra_attribute_values"] = sum(dim[key]*nr_attr[key] for key in dim)

    dim.update(default_dimensions)
    scenario_num = args.first_scenario_id
    eb = _eb.create(db_dir / "emmebank", dim)
    eb.text_encoding = 'utf-8'
    eb.title = project_name
    eb.coord_unit_length = 0.001
    eb.create_scenario(scenario_num)
    emmebank_path = eb.path
    eb.dispose()
    EmmeProject(project_path, emmebank_path, project_name, visible=True)

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
        "--project-name",
        type=str,
        help="Name of LEM project. Influences name of database directory"),
    parser.add_argument(
        "--submodel",
        type=str,
        help="Name of submodel, used for choosing appropriate database dimensions"),
    parser.add_argument(
        "--emme-path",
        type=str,
        help="Filepath to folder where EMME project will be created"),
    parser.add_argument(
        "--number-of-emme-scenarios",
        type=int,
        help="Number of scenarios in the emmebank"),
    parser.add_argument(
        "-s", "--separate-emme-scenarios",
        action="store_true",
        help="Using this flag enables saving network time-period specific results in separate EMME scenarios."),
    parser.add_argument(
        "--first-scenario-id",
        type=int,
        help="First EMME project scenario ID"),
    parser.set_defaults(
        **{key.lower(): val for key, val in config.items()})
    args = parser.parse_args()
    log.initialize(args)
    log.debug(utils.config.dump(vars(args)))

    create_emme_project(args)