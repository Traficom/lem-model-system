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

def create_emme_project(args):
    logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO)
    project_dir = args.emme_path
    project_name = args.submodel
    db_dir = os.path.join(project_dir, project_name, "Database")
    project_path = _app.create_project(project_dir, project_name)
    os.makedirs(db_dir)
    default_dimensions = {
        "scalar_matrices": 100, 
        "origin_matrices": 100, 
        "destination_matrices": 100, 
        "full_matrices": 600, 
        "scenarios": args.number_of_emme_scenarios, 
        "centroids": 10000, 
        "regular_nodes": 989999,
        "links": 2000000, 
        "turn_entries": 1, 
        "transit_vehicles": 40, 
        "transit_lines": 40000, 
        "transit_segments": 2000000, 
        "extra_attribute_values": 24120015,
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
            "extra_attribute_values": 30000000,
        },
        "lounais_suomi": {
            "centroids": 3000, 
            "regular_nodes": 45000, 
            "links": 150000,
            "transit_lines": 3000,
            "transit_segments": 250000,
            "extra_attribute_values": 30000000,            
        },
        "ita_suomi": {
            "centroids": 3300, 
            "regular_nodes": 45000, 
            "links": 150000,
            "transit_lines": 3300,
            "transit_segments": 300000,
            "extra_attribute_values": 30000000,            
        },
        "pohjois_suomi": {
            "centroids": 3000, 
            "regular_nodes": 40000, 
            "links": 150000,
            "transit_lines": 2500,
            "transit_segments": 200000,
            "extra_attribute_values": 30000000,                  
        },
        "koko_suomi": {
            "centroids": 10000, 
            "regular_nodes": 120000, 
            "links": 350000,
            "transit_lines": 8000,
            "transit_segments": 700000,
            "extra_attribute_values": 70000000,                  
        },
        "freight": {
            "centroids": 320,
            "regular_nodes": 20000,
            "links": 55000,
            "transit_lines": 7000,
            "transit_segments": 500000,
            "extra_attribute_values": 25000000,
        }
    }
    dim = {**default_dimensions, **submodel_dimensions[args.submodel]}
    scenario_num = args.first_scenario_id
    eb = _eb.create(os.path.join(db_dir, "emmebank"), dim)
    eb.text_encoding = 'utf-8'
    eb.coord_unit_length = 0.001
    scen = eb.create_scenario(scenario_num)
    emmebank_path = eb.path
    eb.dispose()
    EmmeProject(project_path, emmebank_path)

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
    # HELMET scenario input data
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
        "--first-scenario-id",
        type=int,
        default=config.FIRST_SCENARIO_ID,
        help="First EMME project scenario ID"),
    args = parser.parse_args()

    args_dict = vars(args)
    for key in args_dict:
        log.debug("{}={}".format(key, args_dict[key]))

    create_emme_project(args)