from __future__ import annotations
from typing import Any, Dict, Union
import parameters.assignment as param
from assignment.datatypes.journey_level import JourneyLevel


class TransitSpecification:
    """
    Transit assignment specification.
    
    Two journey levels are added at a later stage.
    At the second level an extra boarding penalty is implemented,
    hence a transfer penalty. Waiting time length is also different. 
    Walk only trips are not allowed.

    Parameters
    ----------
    transit_class : str
        Name of transit class (transit_work/transit_leisure/...)
    segment_results : dict
        key : str
            Segment result (transit_volumes/...)
        value : str
            Extra attribute name (@transit_work_vol_aht/...)
    park_and_ride_results : str or False (optional)
        Extra attribute name for park-and-ride aux volume if
        this is park-and-ride assignment, else False
    headway_attribute : str
        Line attribute where headway is stored
    emme_matrices : dict
        key : str
            Impedance type (time/cost/dist/...)
        value : str
            Emme matrix id
    count_zone_boardings : bool (optional)
        Whether assignment is performed only to count fare zone boardings
    """
    def __init__(self, 
                 transit_class: str,
                 segment_results: Dict[str,str],
                 park_and_ride_results: Union[str, bool],
                 headway_attribute: str,
                 emme_matrices: Dict[str, Union[str, Dict[str, str]]], 
                 count_zone_boardings: bool = False):
        no_penalty = dict.fromkeys(["at_nodes", "on_lines", "on_segments"])
        no_penalty["global"] = {
            "penalty": 0, 
            "perception_factor": 1,
        }
        modes = (param.local_transit_modes + param.aux_modes
                 + param.long_dist_transit_modes[transit_class])
        self.transit_spec: Dict[str, Any] = {
            "type": "EXTENDED_TRANSIT_ASSIGNMENT",
            "modes": modes,
            "demand": emme_matrices["demand"],
            "waiting_time": {
                "headway_fraction": 1,
                "effective_headways": headway_attribute,
                "spread_factor": 1,
                "perception_factor": 1,
            },
            "boarding_time": {
                "global": None,
                "at_nodes": None,
                "on_lines": {
                    "penalty": param.boarding_penalty_attr + transit_class,
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
                "perception_factor": (param.vot_inv[param.vot_classes[
                    transit_class]]),
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
        if park_and_ride_results:
            self.transit_spec["modes"].append(param.park_and_ride_mode)
            self.transit_spec["results"] = {
                "aux_transit_volumes_by_mode": [{
                    "mode": param.park_and_ride_mode,
                    "volume": park_and_ride_results,
                }],
            }
        self.transit_spec["journey_levels"] = [JourneyLevel(
                level, transit_class, headway_attribute, park_and_ride_results,
                count_zone_boardings).spec
            for level in range(6)]
        self.ntw_results_spec = {
            "type": "EXTENDED_TRANSIT_NETWORK_RESULTS",
            "on_segments": segment_results,
            }
        subset = "by_mode_subset"
        self.transit_result_spec = {
            "type": "EXTENDED_TRANSIT_MATRIX_RESULTS",
            subset: {
                "modes": modes,
                "distance": emme_matrices["dist"],
            },
        }
        if count_zone_boardings:
            bcost = "actual_total_boarding_costs"
            self.transit_result_spec[subset][bcost] = emme_matrices[bcost]
        else:
            self.transit_result_spec["total_impedance"] = emme_matrices["gen_cost"]
            icost = "actual_in_vehicle_costs"
            self.transit_result_spec[subset][icost] = emme_matrices["cost"]
            for trip_part, matrix_id in emme_matrices["total"].items():
                self.transit_result_spec[trip_part] = matrix_id
            for trip_part, matrix_id in emme_matrices[subset].items():
                self.transit_result_spec[subset][trip_part] = matrix_id
