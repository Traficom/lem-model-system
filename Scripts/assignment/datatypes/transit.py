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
        self._create_matrices()

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
        num_proc = "number_of_processors"
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
            "performance_settings": {
                num_proc: param.performance_settings[num_proc],
            },
        }
        aux_transit_times = []
        aux_perception_factor = (param.aux_time_perception_factor
            if name in param.local_transit_classes
            else param.aux_time_perception_factor_long)
        for mode in param.aux_modes:
            aux_transit_times.append({
                "mode": mode,
                "cost": None,
                "cost_perception_factor": 1.0,
                "time": param.aux_transit_time_attr,
                "time_perception_factor": aux_perception_factor})
        self.transit_spec["aux_transit_by_mode"] = aux_transit_times
        self._add_park_and_ride()
        self.transit_spec["journey_levels"] = [JourneyLevel(
                level, self.name, self.park_and_ride_results).spec
            for level in range(7)]
        self.ntw_results_spec = {
            "type": "EXTENDED_TRANSIT_NETWORK_RESULTS",
            "analyzed_demand": self.demand.id,
            "on_segments": self.segment_results,
            }
        result_specs = self._add_matrix_specs(modes)
        for matrix_subset, spec in zip(
                param.transit_impedance_matrices.values(), result_specs):
            for mtx_type, longer_name in matrix_subset.items():
                if save_extra_matrices or mtx_type in param.impedance_output:
                    mtx = self._create_matrix(mtx_type)
                    spec[longer_name] = mtx.id

    def _create_matrices(self):
        self.num_board = self._create_matrix("num_board")
        self.gen_cost = self._create_matrix("gen_cost")
        self.inv_cost = self._create_matrix("inv_cost")
        self.board_cost = self._create_matrix("board_cost")

    def _add_park_and_ride(self):
        self.park_and_ride_results = False

    def _add_matrix_specs(self, modes):
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
        return [
            self.transit_result_spec,
            self.transit_result_spec[subset],
        ]

    def get_matrices(self):
        transfer_penalty = (param.transfer_penalty[self.name]
                            * (self.num_board.data > 0)).astype("float32")
        cost = self.inv_cost.data + self.board_cost.data
        time = self.gen_cost.data - self.vot_inv*cost - transfer_penalty
        time[cost > 999999] = 999999
        mtxs = {"time": time, "cost": cost}
        for mtx_name in param.impedance_output:
            if mtx_name in self._matrices:
                mtxs[mtx_name] = self._matrices[mtx_name].data
        self._soft_release_matrices()
        return mtxs


class MixedMode(TransitMode):
    def __init__(self, name: str, assignment_period: AssignmentPeriod,
                 day_scenario: Scenario, dist_unit_cost: float,
                 save_matrices: bool = False, save_extra_matrices: bool = False):
        TransitMode.__init__(
            self, name, assignment_period, day_scenario, save_matrices,
            save_extra_matrices)
        self.dist_unit_cost = dist_unit_cost

    def _create_matrices(self):
        TransitMode._create_matrices(self)
        self.car_time = self._create_matrix("car_time")
        self.car_dist = self._create_matrix("car_dist")
        self.loc_time = self._create_matrix("loc_time")
        self.aux_time = self._create_matrix("aux_time")
        self.park_cost = self._create_matrix("park_cost")

    def _add_park_and_ride(self):
        aux_perception_factor = (param.aux_time_perception_factor_long
            if 'l' in self.transit_spec["modes"]
            else param.aux_time_perception_factor_car)
        aux_transit_times = self.transit_spec["aux_transit_by_mode"]
        aux_transit_times.append({
            "mode": param.park_and_ride_mode,
            "time": param.aux_car_time_attr,
            "time_perception_factor": aux_perception_factor,
        })
        if "taxi" not in self.name:
            for mode_cost in aux_transit_times:
                mode_cost["cost"] = param.park_cost_attr_l
                mode_cost["cost_perception_factor"] = self.vot_inv
        self.park_and_ride_results = f"@{self.name[0]}{self.name[2:]}_aux"
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

    def _add_matrix_specs(self, modes):
        subset = "by_mode_subset"
        self.local_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            subset: {
                "modes": param.local_transit_modes,
                "perceived_aux_transit_times": self.aux_time.id,
                "perceived_in_vehicle_times": self.loc_time.id,
            },
        }
        self.park_and_ride_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            subset: {
                "modes": [param.park_and_ride_mode],
                "distance": self.car_dist.id,
                "actual_aux_transit_times": self.car_time.id,
                "actual_aux_transit_costs": self.park_cost.id,
            },
        }
        result_specs: list = TransitMode._add_matrix_specs(self, modes)
        result_specs += [
            self.local_result_spec[subset],
            self.park_and_ride_spec[subset],
        ]
        return result_specs

    def get_matrices(self):
        car_cost = self.dist_unit_cost * self.car_dist.data
        mtxs = TransitMode.get_matrices(self)
        mtxs["cost"] += car_cost
        return mtxs
