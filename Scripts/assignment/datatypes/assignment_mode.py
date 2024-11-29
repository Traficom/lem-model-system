from typing import Dict, Union

import parameters.assignment as param
from assignment.datatypes.path_analysis import PathAnalysis
from assignment.datatypes.journey_level import JourneyLevel
from assignment.datatypes.emme_matrix import EmmeMatrix, PermanentEmmeMatrix


LENGTH_ATTR = "length"


class AssignmentMode:
    def __init__(self, name, emme_scenario, emme_project, time_period, save_matrices=False):
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


class CarMode(AssignmentMode):
    def __init__(self, name, emme_scenario, emme_project, time_period, dist_unit_cost, include_toll_cost):
        AssignmentMode.__init__(self, name, emme_scenario, emme_project, time_period)
        self.vot_inv = param.vot_inv[param.vot_classes[self.name]]
        self.gen_cost = self._create_matrix("gen_cost")
        self.dist = self._create_matrix("dist")
        self.dist_unit_cost = dist_unit_cost
        self.include_toll_cost = include_toll_cost
        if include_toll_cost:
            self.toll_cost = self._create_matrix("toll_cost")
            self.link_cost_attr = f"@cost_{self.name[:10]}_{self.time_period}"
            self.emme_project.create_extra_attribute(
                "LINK", self.link_cost_attr, "total cost",
                overwrite=True, scenario=self.emme_scenario)
        self.specify()

    def specify(self):
        perception_factor = self.vot_inv
        try:
            link_cost_attr = self.link_cost_attr
        except AttributeError:
            perception_factor *= self.dist_unit_cost
            link_cost_attr = LENGTH_ATTR
        self.spec = {
            "mode": param.assignment_modes[self.name],
            "demand": self.demand.id,
            "generalized_cost": {
                "link_costs": link_cost_attr,
                "perception_factor": perception_factor,
            },
            "results": {
                "link_volumes": f"@{self.name}_{self.time_period}",
                "od_travel_times": {
                    "shortest_paths": self.gen_cost.id
                }
            },
            "path_analyses": []
        }
        self.add_analysis(LENGTH_ATTR, self.dist.id)
        if self.include_toll_cost:
            self.add_analysis(
                f"@toll_cost_{self.time_period}", self.toll_cost.id)

    def add_analysis (self,
                      link_component: str,
                      od_values: Union[int, str]):
        analysis = PathAnalysis(link_component, od_values)
        self.spec["path_analyses"].append(analysis.spec)

    def get_matrices(self):
        cost = self.dist_unit_cost * self.dist.data
        if self.include_toll_cost:
            cost += self.toll_cost.data
        time = self._get_time(cost)
        m = {"cost": cost, "time": time, **self.dist.item}
        if self.include_toll_cost:
            m.update(self.toll_cost.item)
        self._release_matrices()
        # fix the emme path analysis results
        # (dist and cost are zero if path not found but we want it to
        # be the default value 999999)
        path_not_found = time > 999999
        for mtx_type in ("cost", "dist"):
            m[mtx_type][path_not_found] = 999999
        return m

    def _get_time(self, cost):
        return self.gen_cost.data - self.vot_inv*cost

class TruckMode(CarMode):
    def __init__(self, *args):
        CarMode.__init__(self, *args)
        self.time = self._create_matrix("time")
        self.add_analysis(f"@truck_time_{self.time_period}", self.time.id)

    def _get_time(self, *args):
        return self.time.data

class TransitMode(AssignmentMode):
    def __init__(self, day_scenario, *args):
        AssignmentMode.__init__(self, *args)
        self.vot_inv = param.vot_inv[param.vot_classes[self.name]]
        self.num_board = self._create_matrix("num_board")
        self.gen_cost = self._create_matrix("gen_cost")
        self.inv_cost = self._create_matrix("inv_cost")
        self.board_cost = self._create_matrix("board_cost")
        self.transit_matrices = {}
        for subset, parts in param.transit_impedance_matrices.items():
            self.transit_matrices[subset] = {}
            for mtx_type, longer_name in parts.items():
                self.transit_matrices[subset][longer_name] = self._create_matrix(mtx_type)
        self.specify(day_scenario)

    def specify(self, day_scenario):
        self.segment_results = {}
        for emme_scenario, tp in (
                (self.emme_scenario, self.time_period), (day_scenario, "vrk")):
            for res, attr in param.segment_results.items():
                attr_name = f"@{self.name[:11]}_{attr}_{tp}"
                self.segment_results[res] = attr_name
                self.emme_project.create_extra_attribute(
                    "TRANSIT_SEGMENT", attr_name,
                    f"{self.name} {res}", overwrite=True,
                    scenario=emme_scenario)
                if res != "transit_volumes":
                    self.emme_project.create_extra_attribute(
                        "NODE", f"@{self.name[:10]}n_{attr}_{tp}",
                        f"{self.name} {res}", overwrite=True,
                        scenario=emme_scenario)
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
            subset: {
                "modes": modes,
                "total_impedance": self.gen_cost.id,
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
        for trip_part, matrix in self.transit_matrices["total"].items():
            self.transit_result_spec[trip_part] = matrix.id
        for trip_part, matrix in self.transit_matrices[subset].items():
            self.transit_result_spec[subset][trip_part] = matrix.id
        for trip_part, matrix in self.transit_matrices["local"].items():
            self.local_result_spec[subset][trip_part] = matrix.id

    def get_matrices(self):
        transfer_penalty = ((self.num_board.data > 0)
                            * param.transfer_penalty[self.name])
        cost = self.inv_cost.data + self.board_cost.data
        time = self.gen_cost.data - self.vot_inv*cost - transfer_penalty
        self._release_matrices()
        time[cost > 999999] = 999999
        return {"time": time, "cost": cost}
