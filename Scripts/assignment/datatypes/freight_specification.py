from __future__ import annotations
from typing import Any, Dict, Union

import parameters.assignment as param


class FreightSpecification:
    """
    Freight assignment specification.

    Parameters
    ----------
    modes : dict
        key : str
            One-letter mode ID
        value : str
            Terminal cost attribute name
    emme_matrices : dict
        key : str
            Impedance type (time/cost/dist/...)
        value : str
            Emme matrix id
    """
    def __init__(self,
                 modes: Dict[str, str],
                 emme_matrices: Dict[str, Union[str, Dict[str, str]]]):
        no_penalty = dict.fromkeys(
            ["global", "at_nodes", "on_lines", "on_segments"])
        all_modes = {param.park_and_ride_mode: "truck access"}
        all_modes.update(modes)
        transitions = [{
            "mode": mode,
            "next_journey_level": i,
        } for i, mode in enumerate(all_modes)]
        journey_levels = [{
            "description": all_modes[mode],
            "destinations_reachable": True,
            "transition_rules": transitions,
            "boarding_time": None,
            "boarding_cost": no_penalty.copy(),
            "waiting_time": None,
        } for mode in all_modes]
        # Terminal cost is related to mode that changes the journey level,
        # hence "the other" mode
        terminal_cost_attrs = ([param.terminal_cost_attr]
                               + list(reversed(list(modes.values()))))
        for jl, attr in zip(journey_levels, terminal_cost_attrs):
            jl["boarding_cost"]["on_lines"] = {
                "penalty": attr,
                "perception_factor": 1,
            }
        no_penalty["global"] = {
            "penalty": 0,
            "perception_factor": 1,
        }
        self.spec: Dict[str, Any] = {
            "type": "EXTENDED_TRANSIT_ASSIGNMENT",
            "modes": list(all_modes),
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
                "perception_factor": 30,
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
            "journey_levels": journey_levels,
            "performance_settings": param.performance_settings,
        }
        self.result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": list(modes),
                "distance": emme_matrices["dist"],
                "actual_in_vehicle_times": emme_matrices["time"],
            },
        }
        self.local_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": [param.park_and_ride_mode],
                "distance": emme_matrices["aux_dist"],
                "actual_aux_transit_times": emme_matrices["aux_time"],
            },
        }
        self.ntw_results_spec = {
            "type": "EXTENDED_TRANSIT_NETWORK_RESULTS",
            "analyzed_demand": emme_matrices["demand"],
            "on_links": {},
            "on_segments": {},
        }
