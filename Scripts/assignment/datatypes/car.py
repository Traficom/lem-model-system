from __future__ import annotations
import parameters.assignment as param
from assignment.datatypes.path_analysis import PathAnalysis
from collections.abc import Callable
from typing import Any, Dict, Optional, Union


LENGTH_ATTR = "length"


class Car:
    def __init__(self,
                 perception_factor: float,
                 assignment_mode: str,
                 extra: Callable,
                 emme_matrices: Dict[str, Union[str, Dict[str, str]]],
                 link_costs: Union[str, float]):
        """Car assignment class definition.

        Parameters
        ----------
        ass_class : str
            Assignment class (car_work/car_leisure/van/truck/trailer_truck)
        extra : assignment_period.AssignmentPeriod.extra()
            Function for generating extra attribute name
            for specific assignment period
        emme_matrices : dict
            key : str
                Impedance type (time/cost/dist/...)
            value : str
                Emme matrix id
        link_costs : str or float
            Extra attribute where link cost is found (str) or length
            multiplier to calculate link cost (float)
        """
        try:
            perception_factor *= link_costs
        except TypeError:
            pass
        else:
            link_costs = LENGTH_ATTR
        self.spec: Dict[str, Any] = {
            "mode": assignment_mode,
            "demand": emme_matrices["demand"],
            "generalized_cost": {
                "link_costs": link_costs,
                "perception_factor": perception_factor,
            },
            "results": {
                "link_volumes": extra,
                "od_travel_times": {
                    "shortest_paths": emme_matrices["gen_cost"]
                }
            },
            "path_analyses": []
        }
        self.add_analysis(LENGTH_ATTR, emme_matrices["dist"])
        if link_costs != LENGTH_ATTR:
            self.add_analysis(extra("toll_cost"), emme_matrices["toll_cost"])
    
    def add_analysis (self, 
                      link_component: str, 
                      od_values: Union[int, str]):
        analysis = PathAnalysis(link_component, od_values)
        self.spec["path_analyses"].append(analysis.spec)
