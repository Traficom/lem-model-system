from __future__ import annotations
from typing import TYPE_CHECKING, Dict

import parameters.assignment as param
from assignment.datatypes.assignment_mode import AssignmentMode
from assignment.datatypes.journey_level import JourneyLevel
if TYPE_CHECKING:
    from assignment.assignment_period import AssignmentPeriod
    from assignment.emme_bindings.mock_project import Scenario


class TransitMode(AssignmentMode):
    def __init__(self, name: str, assignment_period: AssignmentPeriod,
                 day_scenario: Scenario, save_matrices: bool = False,
                 save_extra_matrices: bool = False):
        """Initialize transit mode.

        Parameters
        ----------
        name : str
            Mode name
        assignment_period : AssignmentPeriod
            Assignment period to link to the mode
        day_scenario : Scenario
            EMME scenario linked to whole-day time period
        save_matrices : bool (optional)
            Whether matrices will be saved in Emme format for all time periods
        save_extra_matrices : bool (optional)
            Whether extra LOS-component matrices will be saved in Emme format
        """
        AssignmentMode.__init__(self, name, assignment_period, save_matrices)
        self.vot_inv = param.vot_inv[param.vot_classes[self.name]]
        self.num_board = self._create_matrix("num_board")
        self.gen_cost = self._create_matrix("gen_cost")
        self.inv_cost = self._create_matrix("inv_cost")
        self.board_cost = self._create_matrix("board_cost")

        # Create extra attributes
        self.segment_results: Dict[str, str] = {}
        self.node_results: Dict[str, str] = {}
        for scenario, tp in (
                (self.emme_scenario, self.time_period), (day_scenario, "vrk")):
            for res, attr in param.segment_results.items():
                attr_name = f"@{self.name[:11]}_{attr}_{tp}"
                self.segment_results[res] = attr_name
                self.emme_project.create_extra_attribute(
                    "TRANSIT_SEGMENT", attr_name, f"{self.name} {res}",
                    overwrite=True, scenario=scenario)
                if res != "transit_volumes":
                    attr_name = f"@{self.name[:10]}n_{attr}_{tp}"
                    self.node_results[res] = attr_name
                    self.emme_project.create_extra_attribute(
                        "NODE", attr_name, f"{self.name} {res}",
                        overwrite=True, scenario=scenario)

        # Specify
        no_penalty = dict.fromkeys(["at_nodes", "on_lines", "on_segments"])
        no_penalty["global"] = {
            "penalty": 0,
            "perception_factor": 1,
        }
        modes = (param.local_transit_modes + param.aux_modes
                 + param.long_dist_transit_modes[self.name])
        self.transit_spec = {
            "type": "EXTENDED_TRANSIT_ASSIGNMENT",
            "modes": modes,
            "demand": self.demand.id,
            "waiting_time": {
                "headway_fraction": 1,
                "effective_headways": param.effective_headway_attr,
                "spread_factor": 1,
                "perception_factor": 1,
            },
            "boarding_time": {
                "global": None,
                "at_nodes": None,
                "on_lines": {
                    "penalty": param.boarding_penalty_attr + self.name,
                    "perception_factor": 1
                },
                "on_segments": param.extra_waiting_time,
            },
            # Boarding cost is defined for each journey level separately,
            # so here we just set the default to zero.
            "boarding_cost": no_penalty,
            "in_vehicle_time": {
                "perception_factor": 1
            },
            "in_vehicle_cost": {
                "penalty": param.line_penalty_attr,
                "perception_factor": self.vot_inv,
            },
            "aux_transit_time": param.aux_transit_time,
            "flow_distribution_at_origins": {
                "choices_at_origins": "OPTIMAL_STRATEGY",
            },
            "flow_distribution_at_regular_nodes_with_aux_transit_choices": {
                "choices_at_regular_nodes": "OPTIMAL_STRATEGY",
            },
            "flow_distribution_between_lines": {
                "consider_total_impedance": True,
            },
            "journey_levels": None,
            "performance_settings": param.performance_settings,
        }
        if self.name in param.park_and_ride_classes:
            self.park_and_ride_results = f"@{self.name[4:]}_aux"
            self.emme_project.create_extra_attribute(
                "LINK", self.park_and_ride_results, self.name,
                overwrite=True, scenario=self.emme_scenario)
            self.transit_spec["modes"].append(param.park_and_ride_mode)
            self.transit_spec["results"] = {
                "aux_transit_volumes_by_mode": [{
                    "mode": param.park_and_ride_mode,
                    "volume": self.park_and_ride_results,
                }],
            }
        else:
            self.park_and_ride_results = False
        self.transit_spec["journey_levels"] = [JourneyLevel(
                level, self.name, self.park_and_ride_results).spec
            for level in range(6)]
        self.ntw_results_spec = {
            "type": "EXTENDED_TRANSIT_NETWORK_RESULTS",
            "analyzed_demand": self.demand.id,
            "on_segments": self.segment_results,
            }
        subset = "by_mode_subset"
        self.transit_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            "total_impedance": self.gen_cost.id,
            subset: {
                "modes": modes,
                "actual_in_vehicle_costs": self.inv_cost.id,
                "actual_total_boarding_costs": self.board_cost.id,
                "avg_boardings": self.num_board.id,
            },
        }
        self.local_result_spec = {
                "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
                subset: {
                    "modes": param.local_transit_modes,
                },
            }
        result_specs = (
            self.transit_result_spec,
            self.transit_result_spec[subset],
            self.local_result_spec[subset],
        )
        for matrix_subset, spec in zip(
                param.transit_impedance_matrices.values(), result_specs):
            for mtx_type, longer_name in matrix_subset.items():
                if save_extra_matrices or mtx_type in param.impedance_output:
                    mtx = self._create_matrix(mtx_type)
                    spec[longer_name] = mtx.id

    def get_matrices(self):
        transfer_penalty = ((self.num_board.data > 0)
                            * param.transfer_penalty[self.name])
        cost = self.inv_cost.data + self.board_cost.data
        time = self.gen_cost.data - self.vot_inv*cost - transfer_penalty
        time[cost > 999999] = 999999
        mtxs = {"time": time, "cost": cost}
        for mtx_name in param.impedance_output:
            if mtx_name in self._matrices:
                mtxs[mtx_name] = self._matrices[mtx_name].data
        self._release_matrices()
        return mtxs
