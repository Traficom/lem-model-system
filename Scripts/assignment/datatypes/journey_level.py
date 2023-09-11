from __future__ import annotations
from typing import Any, Dict, Union
import parameters.assignment as param


NOT_BOARDED, PARKED, BOARDED_LOCAL, BOARDED_LONG_D, LEFT, FORBIDDEN = range(6)
DESCRIPTION = [
    "Not boarded yet",
    "Parked",
    "Boarded local service",
    "Boarded long-distance service",
    "Left transit system",
    "Forbidden",
]
DESTINATIONS_REACHABLE = [False, False, True, True, True, False]


class JourneyLevel:
    """
    Journey level specification for transit assignment.

    Parameters
    ----------
    level : int
        Journey level: 0 - not boarded yet, 1 - parked,
        2 - boarded local service, 3 - boarded long-distance service,
        3 - left transit system, 4 - forbidden (virtual level)
    transit_class : str
        Name of transit class (transit_work/transit_leisure/...)
    headway_attribute : str
        Line attribute where headway is stored
    park_and_ride : str or False (optional)
        Extra attribute name for park-and-ride aux volume if
        this is park-and-ride assignment, else False
    count_zone_boardings : bool (optional)
        Whether assignment is performed only to count fare zone boardings
    """
    def __init__(self, level: int, transit_class: str, headway_attribute: str,
            park_and_ride: Union[str, bool] = False,
            count_zone_boardings: bool = False):
        # Boarding transit modes allowed only on levels 0-3
        next = BOARDED_LOCAL if level <= BOARDED_LONG_D else FORBIDDEN
        transitions = [{
                "mode": mode,
                "next_journey_level": next,
            } for mode in param.local_transit_modes]
        next = BOARDED_LONG_D if level <= BOARDED_LONG_D else FORBIDDEN
        transitions += [{
                "mode": mode,
                "next_journey_level": next,
            } for mode in param.long_dist_transit_modes[transit_class]]
        if park_and_ride:
            if "first_mile" in park_and_ride:
                # Park-and-ride (car) mode allowed only on level 0.
                car = FORBIDDEN if level >= PARKED else NOT_BOARDED
                # If we want parking to be allowed only on specific links
                # (i.e., park-and-ride facilities), we should specify an
                # own mode for these links. For now, parking is allowed
                # on all links where walking to a stop is possible.
                walk = PARKED if level == NOT_BOARDED else level
            elif "last_mile" in park_and_ride:
                # Transfer to park-and-ride (car) mode only allowed after first
                # boarding. If we want parking to be allowed only on specific
                # links, we should specify an own mode for these links.
                # For now, parking is allowed on all links where walking
                # from a stop is possible.
                car = FORBIDDEN if level in (NOT_BOARDED, FORBIDDEN) else LEFT
                walk = FORBIDDEN if level == LEFT else level
            transitions.append({
                "mode": param.park_and_ride_mode,
                "next_journey_level": car,
            })
        else:
            # Walk modes do not normally affect journey level transitions
            walk = level
        transitions += [{
                "mode": mode,
                "next_journey_level": walk,
            } for mode in param.aux_modes]
        self.spec = {
            "description": DESCRIPTION[level],
            "destinations_reachable": DESTINATIONS_REACHABLE[level],
            "transition_rules": transitions,
            "boarding_time": None,
            "boarding_cost": {
                "global": None,
                "at_nodes": None,
                "on_lines": {
                    "penalty": param.board_fare_attr,
                    "perception_factor": param.vot_inv[param.vot_classes[
                        transit_class]],
                },
                "on_segments": None,
            },
            "waiting_time": None,
        }
        if level == BOARDED_LOCAL:
            # Free transfers within local transit
            (self.spec["boarding_cost"]
                      ["on_lines"]["penalty"]) =  param.board_long_dist_attr
        if count_zone_boardings:
            self.spec["boarding_cost"]["global"] = None
            self.spec["boarding_cost"]["at_nodes"] = {
                "penalty": param.is_in_transit_zone_attr,
                "perception_factor": 0,
            }

