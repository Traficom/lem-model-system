from __future__ import annotations
from typing import TYPE_CHECKING, Dict

import parameters.assignment as param
from assignment.datatypes.path_analysis import PathAnalysis
from assignment.datatypes.emme_matrix import EmmeMatrix, PermanentEmmeMatrix
if TYPE_CHECKING:
    from assignment.emme_bindings.emme_project import EmmeProject
    from assignment.emme_bindings.mock_project import Scenario


LENGTH_ATTR = "length"


class AssignmentMode:
    def __init__(self, name: str, emme_scenario: Scenario,
                 emme_project: EmmeProject, time_period: str,
                 save_matrices: bool = False):
        self.name = name
        self.emme_scenario = emme_scenario
        self.emme_project = emme_project
        self.time_period = time_period
        self._save_matrices = save_matrices
        self._matrices: Dict[str, EmmeMatrix] = {}
        self.demand = PermanentEmmeMatrix(
            "demand", f"demand_{self.name}_{self.time_period}",
            self.emme_project, self.emme_scenario.id, default_value=0)

    def _create_matrix(self, mtx_type, default_value=999999):
        args = (
            mtx_type, f"{mtx_type}_{self.name}_{self.time_period}",
            self.emme_project, self.emme_scenario.id, default_value)
        mtx = (PermanentEmmeMatrix(*args) if self._save_matrices
               else EmmeMatrix(*args))
        self._matrices[mtx_type] = mtx
        return mtx

    def init_matrices(self):
        for mtx in self._matrices.values():
            mtx.init()

    def _release_matrices(self):
        for mtx in self._matrices.values():
            mtx.release()


class BikeMode(AssignmentMode):
    def __init__(self, *args):
        AssignmentMode.__init__(self, *args)
        self.dist = self._create_matrix("dist")
        self.time = self._create_matrix("time")
        self.specify()

    def specify(self):
        self.spec = {
            "type": "STANDARD_TRAFFIC_ASSIGNMENT",
            "classes": [
                {
                    "mode": param.main_mode,
                    "demand": self.demand.id,
                    "results": {
                        "od_travel_times": {
                            "shortest_paths": self.time.id,
                        },
                        "link_volumes": f"@{self.name}_{self.time_period}",
                    },
                    "analysis": {
                        "results": {
                            "od_values": self.dist.id,
                        },
                    },
                }
            ],
            "path_analysis": PathAnalysis(LENGTH_ATTR).spec,
            "stopping_criteria": {
                "max_iterations": 1,
                "best_relative_gap": 1,
                "relative_gap": 1,
                "normalized_gap": 1,
            },
            "performance_settings": param.performance_settings
        }

    def get_matrices(self):
        return {**self.dist.item, **self.time.item}


class WalkMode(AssignmentMode):
    def __init__(self, *args):
        AssignmentMode.__init__(self, *args)
        self.dist = self._create_matrix("dist")
        self.time = self._create_matrix("time")
        self.specify()

    def specify(self):
        self.spec = {
            "type": "STANDARD_TRANSIT_ASSIGNMENT",
            "modes": param.aux_modes,
            "demand": self.demand.id,
            "waiting_time": {
                "headway_fraction": 0.01,
                "effective_headways": "hdw",
                "perception_factor": 0,
            },
            "boarding_time": {
                "penalty": 0,
                "perception_factor": 0,
            },
            "aux_transit_time": {
                "perception_factor": 1,
            },
            "od_results": {
                "transit_times": self.time.id,
            },
            "strategy_analysis": {
                "sub_path_combination_operator": "+",
                "sub_strategy_combination_operator": "average",
                "trip_components": {
                    "aux_transit": "length",
                },
                "selected_demand_and_transit_volumes": {
                    "sub_strategies_to_retain": "ALL",
                    "selection_threshold": {
                        "lower": None,
                        "upper": None,
                    },
                },
                "results": {
                    "od_values": self.dist.id,
                },
            },
        }

    def get_matrices(self):
        return {**self.dist.item, **self.time.item}
