from __future__ import annotations
from typing import Any, Dict, Union
import parameters.assignment as param


class FreightSpecification:
    """
    Freight assignment specification.

    Parameters
    ----------
    mode : str
        One-letter mode ID
    emme_matrices : dict
        key : str
            Impedance type (time/cost/dist/...)
        value : str
            Emme matrix id
    aux_result : str
        Name of extra attribute, where aux volume is to be stored
    """
    def __init__(self,
                 mode: str,
                 emme_matrices: Dict[str, Union[str, Dict[str, str]]],
                 aux_result: str):
        journey_levels = [{
            "description": name,
            "destinations_reachable": True,
            "transition_rules": [
                {
                    "mode": param.park_and_ride_mode,
                    "next_journey_level": 0,
                },
                {
                    "mode": mode,
                    "next_journey_level": 1,
                },
            ],
            "boarding_time": None,
            "boarding_cost": None,
            "waiting_time": None,
        } for name in ("truck transport", "train/ship transport")]
        journey_levels[0]["boarding_cost"] = {
            "global": None,
            "at_nodes": {
                "penalty": param.terminal_cost_attr,
                "perception_factor": 1,
            },
            "on_lines": None,
            "on_segments": None,
        }
        no_penalty = dict.fromkeys(["at_nodes", "on_lines", "on_segments"])
        no_penalty["global"] = {
            "penalty": 0,
            "perception_factor": 1,
        }
        self.spec: Dict[str, Any] = {
            "type": "EXTENDED_TRANSIT_ASSIGNMENT",
            "modes": [mode, param.park_and_ride_mode],
            "demand": emme_matrices["demand"],
            "waiting_time": {
                "headway_fraction": 0.1,
                "effective_headways": "hdw",
                "spread_factor": 1,
                "perception_factor": 0,
            },
            "boarding_time": no_penalty,
            "boarding_cost": no_penalty,
            "in_vehicle_time": {
                "perception_factor": 1,
            },
            "aux_transit_time": {
                "perception_factor": 10,
            },
            "flow_distribution_at_origins": {
                "choices_at_origins": "OPTIMAL_STRATEGY",
            },
            "flow_distribution_at_regular_nodes_with_aux_transit_choices": {
                "choices_at_regular_nodes": "OPTIMAL_STRATEGY",
            },
            "flow_distribution_between_lines": {
                "consider_total_impedance": False
            },
            "results": {
                "aux_transit_volumes_by_mode": [
                    {
                        "mode": param.park_and_ride_mode,
                        "volume": aux_result,
                    }
                ]
            },
            "journey_levels": journey_levels,
            "performance_settings": param.performance_settings,
        }
        self.result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": mode,
                "distance": emme_matrices["dist"],
            },
        }
        self.local_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": param.park_and_ride_mode,
                "distance": emme_matrices["aux_dist"],
            },
        }
