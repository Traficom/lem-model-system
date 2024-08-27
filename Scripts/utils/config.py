import os
from pathlib import Path
import json
import subprocess


def read_from_file(path=Path(__file__).parent.parent / "dev-config.json"):
    """Read config parameters from json file.

    Parameters
    ----------
    path : Path (optional)
        Path where json file is found (default: Scripts/dev-config.json)

    Returns
    -------
    Config
        Config object with parameters set from file
    """
    with open(path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return Config(config)


class Config:
    """Container for config parameters.

    The parameters are object variables with CAPS_LOCK,
    which means they should not be modified.
    For clarity the normally used parameters are explicitly initialized
    (to None). However, during `Config` initialization, these variables are
    read from a dictionary and hence strictly speaking modified once.

    Parameters
    ----------
    config : dict
        key : str
            Parameter name (e.g., HELMET_VERSION)
        value : str/bool/int/float
            Parameter value
    """

    def __init__(self, config):
        self.HELMET_VERSION = None
        self.SCENARIO_NAME = None
        self.ITERATION_COUNT = None
        self.MAX_GAP = None
        self.REL_GAP = None
        self.LOG_LEVEL = None
        self.LOG_FORMAT = None
        self.BASELINE_DATA_PATH = None
        self.FORECAST_DATA_PATH = None
        self.RESULTS_PATH = None
        self.SUBMODEL = None
        self.EMME_PROJECT_PATH = None
        self.FIRST_SCENARIO_ID = None
        self.FIRST_MATRIX_ID = None
        self.END_ASSIGNMENT_ONLY = False
        self.LONG_DIST_DEMAND_FORECAST = None
        self.FREIGHT_MATRIX_PATH = None
        self.STORED_SPEED_ASSIGNMENT = False
        self.RUN_AGENT_SIMULATION = False
        self.DO_NOT_USE_EMME = False
        self.SEPARATE_EMME_SCENARIOS = False
        self.SAVE_MATRICES_IN_EMME = False
        self.DELETE_STRATEGY_FILES = False
        self.USE_FIXED_TRANSIT_COST = False
        self.DELETE_EXTRA_MATRICES = False
        for key in config.pop("OPTIONAL_FLAGS"):
            self.__dict__[key] = True
        for key in config:
            self.__dict__[key] = config[key]

    @property
    def VERSION(self):
        """HELMET version number from git tag or dev_config.json."""
        os.chdir(Path(__file__).parent)
        try:
            # If model system is in a git repo
            return subprocess.check_output(
                ["git", "describe", "--tags"], stderr=subprocess.STDOUT,
                text=True)
        except (subprocess.CalledProcessError, WindowsError):
            # If model system is downloaded with helmet-ui
            return self.HELMET_VERSION
