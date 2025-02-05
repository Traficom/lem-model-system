from __future__ import annotations
from typing import Any, Dict
import parameters.assignment as param
from assignment.datatypes.car import CarMode

class CarSpecification:

    def __init__(self, modes: Dict[str, CarMode]):
        """
        Car assignment specification.

        Parameters
        ----------
        modes : dict
            key : str
                    Assignment class (car_work/transit_leisure/...)
            value : CarMode
                Assignment mode to add to specification
        """
        self._modes = modes
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
        specs = []
        for mode in param.car_and_van_classes:
            self._modes[mode].init_matrices()
            specs.append(self._modes[mode].spec)
        self._spec["classes"] = specs
        return self._spec

    def truck_spec(self) -> Dict[str, Any]:
        specs = []
        for mode in param.truck_classes:
            self._modes[mode].init_matrices()
            specs.append(self._modes[mode].spec)
        self._spec["classes"] = specs
        return self._spec

