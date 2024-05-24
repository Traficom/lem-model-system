from argparse import ArgumentParser, ArgumentTypeError
import sys
from pathlib import Path

import utils.config
import utils.log as log
from assignment.emme_assignment import EmmeAssignmentModel
from assignment.mock_assignment import MockAssignmentModel
from modelsystem import ModelSystem, AgentModelSystem
from datahandling.matrixdata import MatrixData


BASE_ZONEDATA_DIR = "2018_zonedata"


def main(args):
    if args.end_assignment_only:
        iterations = 0
    elif args.free_flow_assignment or args.stored_speed_assignment:
        iterations = 1
    elif args.iterations > 0:
        iterations = args.iterations
    else:
        raise ArgumentTypeError(
            "Iteration number {} not valid".format(args.iterations))
    base_zonedata_path = Path(args.baseline_data_path, BASE_ZONEDATA_DIR)
    base_matrices_path = Path(args.baseline_data_path, "Matrices")
    forecast_zonedata_path = Path(args.forecast_data_path)
    results_path = Path(args.results_path, args.scenario_name)
    emme_project_path = Path(args.emme_path)
    log_extra = {
        "status": {
            "name": args.scenario_name,
            "state": "starting",
            "current": 0,
            "completed": 0,
            "failed": 0,
            "total": iterations,
            "log": log.filename,
            "converged": 0,
        }
    }
    # Check input data folders/files exist
    if not base_zonedata_path.is_dir():
        raise NameError(
            "Baseline zonedata directory '{}' does not exist.".format(
                base_zonedata_path))
    if not base_matrices_path.is_dir():
        raise NameError(
            "Baseline zonedata directory '{}' does not exist.".format(
                base_matrices_path))
    if not forecast_zonedata_path.is_dir():
        raise NameError(
            "Forecast data directory '{}' does not exist.".format(
                forecast_zonedata_path))
    # Choose and initialize the Traffic Assignment (supply)model
    kwargs = {
        "use_free_flow_speeds": args.free_flow_assignment,
        "delete_extra_matrices": args.delete_extra_matrices,
    }
    if args.free_flow_assignment:
        kwargs["time_periods"] = ["vrk"]
    if args.do_not_use_emme:
        log.info("Initializing MockAssignmentModel...")
        mock_result_path = results_path / "Matrices" / args.submodel
        if not mock_result_path.is_dir():
            raise NameError(
                "Mock Results directory {} does not exist.".format(
                    mock_result_path))
        ass_model = MockAssignmentModel(MatrixData(mock_result_path), **kwargs)
    else:
        if not emme_project_path.is_file():
            raise NameError(
                ".emp project file not found in given '{}' location.".format(
                    emme_project_path))
        log.info("Initializing Emme...")
        from assignment.emme_bindings.emme_project import EmmeProject
        ass_model = EmmeAssignmentModel(
            EmmeProject(emme_project_path),
            first_scenario_id=args.first_scenario_id,
            separate_emme_scenarios=args.separate_emme_scenarios,
            save_matrices=True,
            first_matrix_id=args.first_matrix_id,
            use_stored_speeds=args.stored_speed_assignment, **kwargs)
    # Initialize model system (wrapping Assignment-model,
    # and providing demand calculations as Python modules)
    # Read input matrices (.omx) and zonedata (.csv)
    log.info("Initializing matrices and models...", extra=log_extra)
    model_args = (forecast_zonedata_path, base_zonedata_path,
                  base_matrices_path, results_path, ass_model, args.submodel)
    model = (AgentModelSystem(*model_args) if args.is_agent_model
             else ModelSystem(*model_args))
    log_extra["status"]["results"] = model.mode_share

    # Run traffic assignment simulation for N iterations,
    # on last iteration model-system will save the results
    log_extra["status"]["state"] = "preparing"
    log.info(
        "Starting simulation with {} iterations...".format(iterations),
        extra=log_extra)
    impedance = model.assign_base_demand(iterations==0)
    log_extra["status"]["state"] = "running"
    i = 1
    while i <= iterations:
        log_extra["status"]["current"] = i
        try:
            log.info("Starting iteration {}".format(i), extra=log_extra)
            impedance = (model.run_iteration(impedance, "last")
                         if i == iterations
                         else model.run_iteration(impedance, i))
            log_extra["status"]["completed"] += 1
        except Exception as error:
            log_extra["status"]["failed"] += 1
            log.error("Exception at iteration {}".format(i), error)
            log.error(
                "Fatal error occured, simulation aborted.", extra=log_extra)
            break
        gap = model.convergence.iloc[-1, :] # Last iteration convergence
        convergence_criteria_fulfilled = gap["max_gap"] < args.max_gap or gap["rel_gap"] < args.rel_gap
        if i == iterations:
            log_extra["status"]['state'] = 'finished'
        elif convergence_criteria_fulfilled:
            iterations = i + 1
        #This is here separately because the model can converge in the last iteration as well
        if convergence_criteria_fulfilled: 
            log_extra["status"]["converged"] = 1
        i += 1
    
    if not log_extra["status"]["converged"]: log.warn("Model has not converged")

    # delete emme matrices
    if not args.save_matrices and not args.do_not_use_emme:
        matrix_ids = [mtx.id for mtx
                      in ass_model.emme_project.modeller.emmebank.matrices()]
        for idx in matrix_ids:
            ass_model.emme_project.modeller.emmebank.delete_matrix(idx)
        log.info("EMME matrices deleted")

    # delete emme strategy files for scenarios
    if args.del_strat_files:
        db_path = emme_project_path.parent / "database"
        for f in db_path.glob("STRAT_s*") + db_path.glob("STRATS_s*/*"):
            try:
                f.unlink()
            except:
                log.info(f"Not able to remove file {f}.")
        log.info(f"Removed strategy files in {db_path}")
    log.info("Simulation ended.", extra=log_extra)


if __name__ == "__main__":
    # Initially read defaults from config file ("dev-config.json")
    # but allow override via command-line arguments
    config = utils.config.read_from_file()
    parser = ArgumentParser(epilog="HELMET model system entry point script.")
    parser.add_argument(
        "--version",
        action="version",
        version="helmet " + str(config.VERSION))
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
    # HELMET scenario metadata
    parser.add_argument(
        "-o", "--end-assignment-only",
        action="store_true",
        default=config.END_ASSIGNMENT_ONLY,
        help="Using this flag runs only end assignment of base demand matrices.",
    )
    parser.add_argument(
        "-f", "--free-flow-assignment",
        action="store_true",
        default=config.FREE_FLOW_ASSIGNMENT,
        help="Using this flag runs assigment with free flow speed."
    )
    parser.add_argument(
        "-x", "--stored-speed-assignment",
        action="store_true",
        default=config.STORED_SPEED_ASSIGNMENT,
        help="Using this flag runs assigment with stored (fixed) speed."
    )
    parser.add_argument(
        "-a", "--run-agent-simulation",
        dest="is_agent_model",
        action="store_true",
        default=config.RUN_AGENT_SIMULATION,
        help="Using this flag runs agent simulations instead of aggregate model.",
    )
    parser.add_argument(
        "-m", "--do-not-use-emme",
        action="store_true",
        default=config.DO_NOT_USE_EMME,
        help="Using this flag runs with MockAssignmentModel instead of EmmeAssignmentModel, not requiring EMME.",
    )
    parser.add_argument(
        "-s", "--separate-emme-scenarios",
        action="store_true",
        default=config.SEPARATE_EMME_SCENARIOS,
        help="Using this flag creates four new EMME scenarios and saves network time-period specific results in them.",
    )
    parser.add_argument(
        "-e", "--save-emme-matrices",
        dest="save_matrices",
        action="store_true",
        default=config.SAVE_MATRICES_IN_EMME,
        help="Using this flag saves matrices for all time periods to Emme-project Database folder.",
    )
    parser.add_argument(
        "-d", "--del-strat-files",
        action="store_true",
        default=config.DELETE_STRATEGY_FILES,
        help="Using this flag deletes strategy files from Emme-project Database folder.",
    )
    parser.add_argument(
        "--scenario-name",
        type=str,
        default=config.SCENARIO_NAME,
        help="Name of HELMET scenario. Influences result folder name and log file name."),
    parser.add_argument(
        "--results-path",
        type=str,
        default=config.RESULTS_PATH,
        help="Path to folder where result data is saved to."),
    # HELMET scenario input data
    parser.add_argument(
        "--submodel",
        type=str,
        default=config.SUBMODEL,
        help="Name of submodel, used for choosing appropriate zone mapping"),
    parser.add_argument(
        "--emme-path",
        type=str,
        default=config.EMME_PROJECT_PATH,
        help="Filepath to .emp EMME-project-file"),
    parser.add_argument(
        "--first-scenario-id",
        type=int,
        default=config.FIRST_SCENARIO_ID,
        help="First (biking) scenario ID within EMME project (.emp)."),
    parser.add_argument(
        "--first-matrix-id",
        type=int,
        default=config.FIRST_MATRIX_ID,
        help="First matrix ID within EMME project (.emp). Used only if --save-emme-matrices."),
    parser.add_argument(
        "--baseline-data-path",
        type=str,
        default=config.BASELINE_DATA_PATH,
        help="Path to folder containing both baseline zonedata and -matrices (Given privately by project manager)"),
    parser.add_argument(
        "--forecast-data-path",
        type=str,
        default=config.FORECAST_DATA_PATH,
        help="Path to folder containing forecast zonedata"),
    parser.add_argument(
        "--iterations",
        type=int,
        default=config.ITERATION_COUNT,
        help="Maximum number of demand model iterations to run (each using re-calculated impedance from traffic and transit assignment)."),
    parser.add_argument(
        "--max-gap",
        type=float,
        default=config.MAX_GAP,
        help="Car work matrix maximum change between iterations"),
    parser.add_argument(
        "--rel-gap",
        type=float,
        default=config.REL_GAP,
        help="Car work matrix relative change between iterations"),
    parser.add_argument(
        "-t", "--use-fixed-transit-cost",
        action="store_true",
        default=config.USE_FIXED_TRANSIT_COST,
        help="Using this flag activates use of pre-calculated (fixed) transit costs."),
    parser.add_argument(
        "--delete-extra-matrices",
        action="store_true",
        default=config.DELETE_EXTRA_MATRICES,
        help="Using this flag means that only matrices needed in demand calculation will be stored.")
    args = parser.parse_args()

    log.initialize(args)
    log.debug("helmet_version=" + str(config.VERSION))
    log.debug('sys.version_info=' + str(sys.version_info[0]))
    log.debug('sys.path=' + str(sys.path))
    args_dict = vars(args)
    for key in args_dict:
        log.debug("{}={}".format(key, args_dict[key]))

    if sys.version_info.major == 3:
        main(args)
    else:
        log.error("Python version not supported, must use version 3")
