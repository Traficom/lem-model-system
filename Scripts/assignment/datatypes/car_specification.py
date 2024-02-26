from __future__ import annotations
from typing import Any, Dict, List, Union
import parameters.assignment as param
from assignment.datatypes.car import Car
from collections.abc import Callable

class CarSpecification:

    def __init__(self,
                 extra: Callable, 
                 emme_matrices: Dict[str, Union[str, Dict[str, str]]],
                 link_costs: Dict[str, Union[str, float]]):
        """
        Car assignment specification.

        Parameters
        ----------
        extra : assignment_period.AssignmentPeriod.extra()
            Function for generating extra attribute name
            for specific assignment period
        emme_matrices : dict
            key : str
                    Assignment class (car_work/transit_leisure/...)
            value : dict
                key : str
                    Impedance type (time/cost/dist/...)
                value : str
                    Emme matrix id
        link_costs : dict
            key : str
                Assignment class (car_work/truck/...)
            value : str or float
                Extra attribute where link cost is found (str) or length
                multiplier to calculate link cost (float)
        """
        self._modes = {m: Car(m, extra, emme_matrices[m], link_costs[m])
                       for m in param.assignment_modes}
        self._spec = {
            "type": "SOLA_TRAFFIC_ASSIGNMENT",
            "background_traffic": {
                "link_component": param.background_traffic_attr,
                "add_transit_vehicles": False,
            },
            "performance_settings": param.performance_settings,
            "stopping_criteria": None, # This is defined later
        }

    def light_spec(self) -> Dict[str, Any]:
        self._spec["classes"] = [self._modes[mode].spec
            for mode in param.car_classes]
        return self._spec

    def truck_spec(self) -> Dict[str, Any]:
        self._spec["classes"] = [self._modes[mode].spec
            for mode in param.truck_classes]
        return self._spec

