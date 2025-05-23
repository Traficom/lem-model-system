from typing import Dict
from pathlib import Path

import utils.log as log
import parameters.assignment as param
from assignment.assignment_period import AssignmentPeriod
from assignment.datatypes.freight_specification import FreightMode


class FreightAssignmentPeriod(AssignmentPeriod):
    def __init__(self, *args, **kwargs):
        AssignmentPeriod.__init__(self, *args, **kwargs)
        for criteria in self.stopping_criteria.values():
                criteria["max_iterations"] = 0

    def prepare(self, dist_unit_cost: Dict[str, float], save_matrices: bool):
        self._prepare_cars(dist_unit_cost, save_matrices)
        network = self.emme_scenario.get_network()
        for line in network.transit_lines():
            mode = line.mode.id
            for cost_attrs in param.freight_modes.values():
                if mode in cost_attrs:
                    cost = param.freight_terminal_cost[mode]
                    line[param.terminal_cost_attr] = cost
                    line[cost_attrs[mode]] = cost
                    break
        self.emme_scenario.publish_network(network)
        self.assignment_modes.update({ass_class: FreightMode(
                ass_class, self, save_matrices)
            for ass_class in param.freight_modes})

    def assign(self):
        self._set_car_vdfs(use_free_flow_speeds=True)
        self._init_truck_times()
        self._assign_trucks()
        self._set_freight_vdfs()
        self._assign_freight()
        mtxs = {tc: self.assignment_modes[tc].get_matrices()
            for tc in param.truck_classes + tuple(param.freight_modes)}
        impedance = {mtx_type: {mode: mtxs[mode][mtx_type]
                for mode in mtxs if mtx_type in mtxs[mode]}
            for mtx_type in (
                "time", "cost", "dist", "aux_time", "aux_dist", "toll_cost",
                "canal_cost")}
        return impedance

    def save_network_volumes(self, commodity_class: str):
        """Save commodity-specific volumes in segment attribute.

        Parameters
        ----------
        commodity_class : str
            Commodity class name
        """
        for ass_class in param.freight_modes:
            spec = self.assignment_modes[ass_class].ntw_results_spec
            attr_name = (commodity_class + ass_class)[:17]
            spec["on_segments"]["transit_volumes"] = "@" + attr_name
            spec["on_links"]["aux_transit_volumes"] = "@a_" + attr_name
            self.emme_project.network_results(
                spec, self.emme_scenario, ass_class)
        attr_name = (commodity_class + "truck")[:17]
        for spec in self._car_spec.truck_specs():
            spec["classes"][0]["results"]["link_volumes"] = "@" + attr_name
            spec["stopping_criteria"] = self.stopping_criteria["coarse"]
            self.emme_project.car_assignment(spec, self.emme_scenario)
        for tc in param.truck_classes:
            self.assignment_modes[tc].get_matrices()

    def output_traversal_matrix(self, demand_modes: set, output_path: Path):
        """Save commodity class specific auxiliary tons for freight modes.
        Result file indicates amount of transported tons with auxiliary 
        mode between gate pair.

        Parameters
        ----------
        demand_modes : set
            commodity specific demand modes
        output_path : Path
            Path where traversal matrices are saved
        """
        spec = {
            "type": "EXTENDED_TRANSIT_TRAVERSAL_ANALYSIS",
            "portion_of_path": "COMPLETE",
            "gates_by_trip_component": {
                "aux_transit": param.freight_gate_attr,
            },
        }
        for ass_class in set(param.freight_modes) & demand_modes:
            output_file = output_path / f"{ass_class}.txt"
            spec["analyzed_demand"] = self.assignment_modes[ass_class].demand.id
            self.emme_project.traversal_analysis(
                spec, output_file, append_to_output_file=False,
                scenario=self.emme_scenario, class_name=ass_class)

    def _set_freight_vdfs(self):
        network = self.emme_scenario.get_network()
        for segment in network.transit_segments():
            segment.transit_time_func = 7
        self.emme_scenario.publish_network(network)

    def _assign_freight(self):
        network = self.emme_scenario.get_network()
        truck_mode = network.mode(param.assignment_modes["truck"])
        park_and_ride_mode = network.mode(param.park_and_ride_mode)
        extra_cost_attr = param.background_traffic_attr.replace("ul", "data")
        for link in network.links():
            if truck_mode in link.modes:
                link.modes |= {park_and_ride_mode}
            else:
                link.modes -= {park_and_ride_mode}
            link[extra_cost_attr] = link[param.extra_freight_cost_attr]
        self.emme_scenario.publish_network(network)
        for i, ass_class in enumerate(param.freight_modes):
            spec = self.assignment_modes[ass_class]
            spec.init_matrices()
            self.emme_project.transit_assignment(
                specification=spec.spec, scenario=self.emme_scenario,
                add_volumes=i, save_strategies=True, class_name=ass_class)
            self.emme_project.matrix_results(
                spec.result_spec, scenario=self.emme_scenario,
                class_name=ass_class)
            self.emme_project.matrix_results(
                spec.local_result_spec, scenario=self.emme_scenario,
                class_name=ass_class)
        log.info("Freight assignment performed for scenario {}".format(
            self.emme_scenario.id))
