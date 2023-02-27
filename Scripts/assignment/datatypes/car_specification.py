import parameters.assignment as param
from assignment.datatypes.car import Car

class CarSpecification:
    """
    Car assignment specification.

    Parameters
    ----------
    demand_mtx : dict
        key : str
            Assignment class (transit_work/transit_leisure)
        value : dict
            id : str
                Emme matrix id
            description : dict
                Matrix description
    result_mtx : dict
        key : str
            Impedance type (time/cost/dist)
        value : dict
            key : str
                Assignment class (transit_work/transit_leisure)
            value : dict
                id : str
                    Emme matrix id
                description : dict
                    Matrix description
    """
    def __init__(self, extra, demand_mtx, result_mtx):
        self._modes = {}
        self._freight_modes = list(param.freight_dist_unit_cost)
        for mode in param.assignment_modes:
            if mode in self._freight_modes:
                kwargs = {
                    "link_costs": "length",
                    "value_of_time_inv": param.freight_dist_unit_time,
                }
            else:
                kwargs = {"link_costs": extra("total_cost")}
            self._modes[mode] = Car(
                mode, extra, demand_mtx, result_mtx, **kwargs)
        self._spec = {
            "type": "SOLA_TRAFFIC_ASSIGNMENT",
            "background_traffic": {
                "link_component": param.background_traffic_attr,
                "add_transit_vehicles": False,
            },
            "performance_settings": param.performance_settings,
            "stopping_criteria": None, # This is defined later
        }

    def spec(self, lightweight=False):
        self._spec["classes"] = [self._modes[mode].spec for mode in self._modes
            if not lightweight or mode not in self._freight_modes]
        return self._spec
