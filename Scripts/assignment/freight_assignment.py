from __future__ import annotations
from typing import Dict, Union, Sequence

import parameters.assignment as param
from assignment.assignment_period import AssignmentPeriod
from assignment.datatypes.freight_specification import FreightSpecification


class FreightAssignmentPeriod(AssignmentPeriod):
    def prepare(self, link_costs: Dict[str, Union[str, float]],
                dist_unit_cost: Dict[str, float],
                terminal_cost_attributes: Sequence[str]):
        """Prepare network for freight assignment.

        Calculate road toll cost and specify car and freight assignment.
        Set segment-wise terminal costs.

        Parameters
        ----------
        link_costs : dict
            key : str
                Assignment class (car_work/truck/...)
            value : str or float
                Extra attribute where link cost is found (str) or length
                multiplier to calculate link cost (float)
        dist_unit_cost : dict
            key : str
                Assignment class (car_work/truck/...)
            value : float
                Length multiplier to calculate link cost
        terminal_cost_attributes : list of str
            Segment extra attribute names for terminal costs
        """
        AssignmentPeriod.prepare(self, link_costs, dist_unit_cost)
        network = self.emme_scenario.get_network()
        for line in network.transit_lines():
            modes = zip(*param.freight_modes.values())
            for attr in terminal_cost_attributes:
                if line.mode.id in next(modes):
                    # If it is a diesel train "line", terminal cost for
                    # switching to electric train is imposed.
                    # If it is an electric train "line", terminal cost for
                    # switching to diesel train is imposed.
                    for segment in line.segments():
                        segment[attr] = segment.i_node[param.terminal_cost_attr]
                    break
        self.emme_scenario.publish_network(network)
        self._freight_specs = {ass_class: FreightSpecification(
                param.freight_modes[ass_class], terminal_cost_attributes,
                self.emme_matrices[ass_class], self.extra(ass_class))
            for ass_class in param.freight_modes}

    def assign(self):
        self._set_car_vdfs(use_free_flow_speeds=True)
        self._init_truck_times()
        self._assign_trucks()
        self._set_freight_vdfs()
        self._assign_freight()
        return {imp_type: self._get_matrices(imp_type, is_last_iteration=True)
            for imp_type in ("time", "cost", "dist")}

    def _set_freight_vdfs(self):
        network = self.emme_scenario.get_network()
        for segment in network.transit_segments():
            segment.transit_time_func = 7
        self.emme_scenario.publish_network(network)

    def _assign_freight(self):
        network = self.emme_scenario.get_network()
        truck_mode = network.mode(param.assignment_modes["truck"])
        park_and_ride_mode = network.mode(param.park_and_ride_mode)
        for link in network.links():
            if truck_mode in link.modes:
                link.modes |= {park_and_ride_mode}
            else:
                link.modes -= {park_and_ride_mode}
        self.emme_scenario.publish_network(network)
        for i, ass_class in enumerate(param.freight_modes):
            spec = self._freight_specs[ass_class]
            self.emme_project.transit_assignment(
                specification=spec.spec, scenario=self.emme_scenario,
                add_volumes=i, save_strategies=True, class_name=ass_class)
            self.emme_project.matrix_results(
                spec.result_spec, scenario=self.emme_scenario,
                class_name=ass_class)
            self.emme_project.matrix_results(
                spec.local_result_spec, scenario=self.emme_scenario,
                class_name=ass_class)
