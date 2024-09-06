from argparse import ArgumentParser
import sys
import os
import logging

import utils.config
import utils.log as log
import assignment.emme_assignment as ass
from assignment.emme_bindings.emme_project import EmmeProject
import inro.emme.desktop.app as _app
import inro.emme.database.emmebank as _eb
import parameters.assignment as param

def create_emme_project(args):
    logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO)
    project_dir = args.emme_path
    project_name = args.project_name
    db_dir = os.path.join(project_dir, project_name, "Database")
    project_path = _app.create_project(project_dir, project_name)
    os.makedirs(db_dir)
    default_dimensions = {
        "scalar_matrices": 100, 
        "origin_matrices": 100, 
        "destination_matrices": 100, 
        "full_matrices": 600, 
        "scenarios": args.number_of_emme_scenarios, 
        "turn_entries": 1, 
        "transit_vehicles": 40, 
        "functions": 99, 
        "operators": 5000, 
        "sola_analyses": 240,
    }
    submodel_dimensions = {
        "uusimaa": {
            "centroids": 3000, 
            "regular_nodes": 40000, 
            "links": 150000,
            "transit_lines": 3000,
            "transit_segments": 250000,
        },
        "lounais_suomi": {
            "centroids": 3000, 
            "regular_nodes": 45000, 
            "links": 150000,
            "transit_lines": 3000,
            "transit_segments": 250000,            
        },
        "ita_suomi": {
            "centroids": 3300, 
            "regular_nodes": 45000, 
            "links": 150000,
            "transit_lines": 3300,
            "transit_segments": 300000,           
        },
        "pohjois_suomi": {
            "centroids": 3000, 
            "regular_nodes": 40000, 
            "links": 150000,
            "transit_lines": 2500,
            "transit_segments": 200000,                 
        },
        "koko_suomi": {
            "centroids": 10000, 
            "regular_nodes": 120000, 
            "links": 350000,
            "transit_lines": 8000,
            "transit_segments": 700000,                
        },
        "freight": {
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
    nr_new_attr = {
        "nodes": nr_transit_classes * (nr_segment_results-1),
        "links": nr_veh_classes + len(param.mixed_mode_classes) + 1,
        "transit_lines": nr_transit_classes + 2,
        "transit_segments": nr_transit_classes*nr_segment_results + 2,
    }
    
    if not args.separate_emme_scenarios:
    # If results from all time periods are stored in same
    # EMME scenario
        for key in nr_new_attr:
            nr_new_attr[key] *= len(param.time_periods) + 1

    # calculate extra attribute dimensions:
    for i in submodel_dimensions:
        submodel_dimensions[i]["extra_attribute_values"] = (submodel_dimensions[i]["links"] * 9 * nr_new_attr["links"]
                                                            + (submodel_dimensions[i]["regular_nodes"] + submodel_dimensions[i]["centroids"]) * 5 * nr_new_attr["nodes"]
                                                            + submodel_dimensions[i]["transit_lines"] * nr_new_attr["transit_lines"]
                                                            + submodel_dimensions[i]["transit_segments"] * nr_new_attr["transit_segments"])

    dim = {**default_dimensions, **submodel_dimensions[args.submodel]}
    scenario_num = args.first_scenario_id
    eb = _eb.create(os.path.join(db_dir, "emmebank"), dim)
    eb.text_encoding = 'utf-8'
    eb.title = project_name
    eb.coord_unit_length = 0.001
    eb.create_scenario(scenario_num)
    emmebank_path = eb.path
    eb.dispose()
    EmmeProject(project_path, emmebank_path, project_name)

if __name__ == "__main__":
    # Initially read defaults from config file ("dev-config.json")
    # but allow override via command-line arguments
    config = utils.config.read_from_file()
    parser = ArgumentParser(epilog="HELMET model system entry point script.")
    # Logging
    parser.add_argument(
        "--log-level",
        choices={"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
        default=config.LOG_LEVEL,
    )
    parser.add_argument(
        "--log-format",
        choices={"TEXT", "JSON"},
        default=config.LOG_FORMAT,
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default=config.PROJECT_NAME,
        help="Name of LEM project. Influences name of database directory"),
    parser.add_argument(
        "--submodel",
        type=str,
        default=config.SUBMODEL,
        help="Name of submodel, used for choosing appropriate database dimensions"),
    parser.add_argument(
        "--emme-path",
        type=str,
        default=config.EMME_PROJECT_PATH,
        help="Filepath to folder where EMME project will be created"),
    parser.add_argument(
        "--number-of-emme-scenarios",
        type=int,
        default=config.NUMBER_OF_EMME_SCENARIOS,
        help="Number of scenarios in the emmebank"),
    parser.add_argument(
        "-s", "--separate-emme-scenarios",
        action="store_true",
        default=config.SEPARATE_EMME_SCENARIOS,
        help="Using this flag enables saving network time-period specific results in separate EMME scenarios."),
    parser.add_argument(
        "--first-scenario-id",
        type=int,
        default=config.FIRST_SCENARIO_ID,
        help="First EMME project scenario ID"),
    args = parser.parse_args()

    args_dict = vars(args)
    for key in args_dict:
        log.debug("{}={}".format(key, args_dict[key]))

    create_emme_project(args)