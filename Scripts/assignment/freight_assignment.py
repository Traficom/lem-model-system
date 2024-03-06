import parameters.assignment as param
from assignment.assignment_period import AssignmentPeriod
from assignment.datatypes.freight_specification import FreightSpecification


class FreightAssignmentPeriod(AssignmentPeriod):
    def prepare(self, *args, **kwargs):
        AssignmentPeriod.prepare(self, *args, **kwargs)
        self._freight_specs = {ass_class: FreightSpecification(
                param.freight_modes[ass_class], self.emme_matrices[ass_class],
                self.extra(ass_class))
            for ass_class in param.freight_modes}

    def assign(self):
        self._set_car_vdfs(use_free_flow_speeds=True)
        self._init_truck_times()
        self._assign_trucks()
        self._set_freight_vdfs()
        self._assign_freight()
        return {imp_type: self._get_matrices(imp_type, is_last_iteration=True)
            for imp_type in ("time", "cost", "dist", "aux_time", "aux_dist")}

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
