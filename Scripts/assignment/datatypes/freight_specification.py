from __future__ import annotations
from typing import Any, Dict

import parameters.assignment as param
from assignment.datatypes.assignment_mode import AssignmentMode


class FreightMode(AssignmentMode):
    def __init__(self, *args, **kwargs):
        AssignmentMode.__init__(self, *args, **kwargs)
        self._include_toll_cost = self.emme_scenario.extra_attribute(
            "@toll_cost_vrk") is not None
        self.dist = self._create_matrix("dist")
        self.aux_dist = self._create_matrix("aux_dist")
        self.time = self._create_matrix("time")
        self.aux_time = self._create_matrix("aux_time")
        self.canal_cost = self._create_matrix("canal_cost")
        no_penalty = dict.fromkeys(
            ["global", "at_nodes", "on_lines", "on_segments"])
        all_modes = {param.park_and_ride_mode: "truck access"}
        modes = param.freight_modes[self.name]
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
        num_proc = "number_of_processors"
        self.spec: Dict[str, Any] = {
            "type": "EXTENDED_TRANSIT_ASSIGNMENT",
            "modes": list(all_modes),
            "demand": self.demand.id,
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
            "in_vehicle_cost": {
                "penalty": param.background_traffic_attr,
                "perception_factor": 1,
            },
            "aux_transit_by_mode": [{
                "mode": param.park_and_ride_mode,
                "time": "@truck_time_vrk",
                "time_perception_factor": param.aux_time_perception_factor_truck,
            }],
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
            "performance_settings": {
                num_proc: param.performance_settings[num_proc],
            },
        }
        self.result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": list(modes),
                "distance": self.dist.id,
                "actual_in_vehicle_times": self.time.id,
                "actual_in_vehicle_costs": self.canal_cost.id,
            },
        }
        self.local_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "by_mode_subset": {
                "modes": [param.park_and_ride_mode],
                "distance": self.aux_dist.id,
                "actual_aux_transit_times": self.aux_time.id,
            },
        }
        if self._include_toll_cost:
            self.spec["aux_transit_by_mode"][0]["cost"] = "@toll_cost_vrk"
            self.spec["aux_transit_by_mode"][0]["cost_perception_factor"] = 1.0
            self.toll_cost = self._create_matrix("toll_cost")
            self.local_result_spec["actual_aux_transit_costs"] = self.toll_cost.id
        self.ntw_results_spec = {
            "type": "EXTENDED_TRANSIT_NETWORK_RESULTS",
            "analyzed_demand": self.demand.id,
            "on_links": {},
            "on_segments": {},
        }

    def get_matrices(self):
        mtxs = {
            **self.dist.item,
            **self.aux_dist.item,
            **self.time.item,
            **self.aux_time.item,
            **self.canal_cost.item,
        }
        if self._include_toll_cost:
            mtxs.update(self.toll_cost.item)
        self._release_matrices()
        return mtxs
