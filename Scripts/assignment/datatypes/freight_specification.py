from __future__ import annotations
from typing import Any, Dict, Sequence, Union

import parameters.assignment as param


class FreightSpecification:
    """
    Freight assignment specification.

    Parameters
    ----------
    modes : list of str
        One-letter mode IDs
    terminal_cost_attributes : list of str
        Segment extra attribute names for terminal costs
    emme_matrices : dict
        key : str
            Impedance type (time/cost/dist/...)
        value : str
            Emme matrix id
    aux_result : str
        Name of extra attribute, where aux volume is to be stored
    """
    def __init__(self,
                 modes: Sequence[str],
                 terminal_cost_attributes: Sequence[str],
                 emme_matrices: Dict[str, Union[str, Dict[str, str]]],
                 aux_result: str):
        no_penalty = dict.fromkeys(
            ["global", "at_nodes", "on_lines", "on_segments"])
        journey_levels = [{
            "description": name,
            "destinations_reachable": True,
            "transition_rules": [
                {
                    "mode": param.park_and_ride_mode,
                    "next_journey_level": 0,
                },
                {
                    "mode": modes[0],
                    "next_journey_level": 1,
                },
                {
                    "mode": modes[1],
                    "next_journey_level": 2,
                },
            ],
            "boarding_time": None,
            "boarding_cost": no_penalty.copy(),
            "waiting_time": None,
        } for name in (
            "truck access",
            "train/ship transport",
            "electric/9m transport")
        ]
        journey_levels[0]["boarding_cost"]["at_nodes"] = {
            "penalty": param.terminal_cost_attr,
            "perception_factor": 1,
        }
        for i, attr in enumerate(terminal_cost_attributes, 1):
            journey_levels[i]["boarding_cost"]["on_segments"] = {
                "penalty": attr,
                "perception_factor": 1,
            }
        no_penalty["global"] = {
            "penalty": 0,
            "perception_factor": 1,
        }
        self.spec: Dict[str, Any] = {
            "type": "EXTENDED_TRANSIT_ASSIGNMENT",
            "modes": modes + [param.park_and_ride_mode],
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
                "modes": modes,
                "distance": emme_matrices["dist"],
            },
        }
        self.local_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": [param.park_and_ride_mode],
                "distance": emme_matrices["aux_dist"],
            },
        }
