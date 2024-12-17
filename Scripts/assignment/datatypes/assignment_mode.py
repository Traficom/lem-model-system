from __future__ import annotations
from typing import TYPE_CHECKING, Dict
from abc import ABC, abstractmethod
import numpy

import parameters.assignment as param
from assignment.datatypes.path_analysis import PathAnalysis
from assignment.datatypes.emme_matrix import EmmeMatrix, PermanentEmmeMatrix
if TYPE_CHECKING:
    from assignment.assignment_period import AssignmentPeriod


LENGTH_ATTR = "length"


class AssignmentMode(ABC):
    """Abstract base class for specifying mode assignment and matrices.

    A mode is assignment-period-specific, so that each mode-period
    combination has its own matrices.

    All modes have one demand matrix, which is "permanent".
    This means that it cannot be initialized or deleted after creation,
    so that additional demand can safely be added to it at any time.
    Demand initialisation is done by setting matrix to zero.
    """
    def __init__(self, name: str, assignment_period: AssignmentPeriod,
                 save_matrices: bool = False):
        """Initialize mode.

        Parameters
        ----------
        name : str
            Mode name
        assignment_period : AssignmentPeriod
            Assignment period to link to the mode
        save_matrices : bool (optional)
            Whether matrices will be saved in Emme format for all time periods
        """
        self.name = name
        self.emme_scenario = assignment_period.emme_scenario
        self.emme_project = assignment_period.emme_project
        self.time_period = assignment_period.name
        self._save_matrices = save_matrices
        self._matrices: Dict[str, EmmeMatrix] = {}
        self.demand = PermanentEmmeMatrix(
            "demand", f"demand_{self.name}_{self.time_period}",
            self.emme_project, self.emme_scenario.id, default_value=0)

    def _create_matrix(self, mtx_type: str, default_value: float = 999999):
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

    @abstractmethod
    def get_matrices(self) -> Dict[str, numpy.ndarray]:
        """Get all LOS matrices.

        Return
        ------
        dict
            key : str
                LOS type (time/cost/...)
            value : numpy.ndarray
                2-D matrix in float32
        """
        pass


class SoftMode(AssignmentMode):
    def __init__(self, *args, **kwargs):
        AssignmentMode.__init__(self, *args, **kwargs)
        self.dist = self._create_matrix("dist")
        self.time = self._create_matrix("time")
        self._specify()

    def _specify(self):
        pass

    def get_matrices(self):
        mtxs = {**self.dist.item, **self.time.item}
        self._release_matrices()
        return mtxs


class BikeMode(SoftMode):
    def _specify(self):
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


class WalkMode(SoftMode):
    def _specify(self):
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
