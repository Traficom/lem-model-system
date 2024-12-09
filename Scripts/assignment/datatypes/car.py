from __future__ import annotations
from typing import TYPE_CHECKING, Union


import parameters.assignment as param
from assignment.datatypes.assignment_mode import AssignmentMode
from assignment.datatypes.path_analysis import PathAnalysis
if TYPE_CHECKING:
    from assignment.emme_bindings.emme_project import EmmeProject
    from assignment.emme_bindings.mock_project import Scenario


LENGTH_ATTR = "length"


class CarMode(AssignmentMode):
    def __init__(self, name: str, emme_scenario: Scenario,
                 emme_project: EmmeProject, time_period: str,
                 dist_unit_cost, include_toll_cost: bool,
                 save_matrices: bool = False):
        AssignmentMode.__init__(
            self, name, emme_scenario, emme_project, time_period, save_matrices)
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
