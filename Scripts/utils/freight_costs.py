import numpy
from typing import Dict


def calc_road_cost(unit_costs: Dict[str, Dict],
                   impedance: Dict[str, numpy.ndarray]):
    """Calculate freight road costs.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (truck/trailer_truck) : unit cost name
                unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll) : numpy 2d matrix

    Returns
    ----------
    road_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    mode_cost = {}
    for mode, params in unit_costs["truck"].items():
        road_cost = sum(impedance[k] * params[k]
                        for k in impedance) / params["avg_load"]
        mode_cost[mode] = ((params["terminal_cost"]*2
                            + road_cost*params["empty_share"])
                           * params["distribution"])
    return sum(mode_cost.values())

def calc_rail_cost(unit_costs: Dict[str, Dict],
                   impedance: Dict[str, numpy.ndarray],
                   impedance_aux: Dict[str, numpy.ndarray]):
    """Calculate freight rail based costs.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (electric_train/diesel_train) : unit cost name
                unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Mode specific Type (time/dist) : numpy 2d matrix
    impedance_aux : Dict[str, numpy.ndarray]
        Auxiliary specific Type (time/dist/toll) : numpy 2d matrix

    Returns
    ----------
    rail_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    mode_cost = {}
    for mode, params in unit_costs["freight_train"].items():
        rail_cost = sum(impedance[k] * params[k]
                        for k in impedance) / params["avg_load"]*2
        mode_cost[mode] = (rail_cost + params["wagon_annual_cost"]
                           + params["terminal_cost"]*2)
    rail_cost = mode_cost["diesel_train"]
    rail_aux_cost = get_aux_cost(unit_costs,
                                 impedance,
                                 impedance_aux)
    return rail_cost + rail_aux_cost

def calc_ship_cost(unit_costs: Dict[str, Dict],
                   impedance: Dict[str, numpy.ndarray],
                   impedance_aux: Dict[str, numpy.ndarray]):
    """Calculate freight ship based costs.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship) : mode
            Mode (other_dry_cargo...) : draught
                draught (4m/7m/9m) : unit cost name
                    unit cost name : unit cost value
    impedance : Dict[str, numpy.ndarray]
        Type (dist/channel) : numpy 2d matrix
    impedance_aux : Dict[str, numpy.ndarray]
        Auxiliary specific Type (time/dist/toll) : numpy 2d matrix

    Returns
    ----------
    ship_cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    mode_cost = {}
    for mode in unit_costs["ship"].keys():
        mode_cost[mode] = {}
        for draught, params in unit_costs["ship"][mode].items():
            ship_cost = (impedance["dist"]*params["time"]
                         / params["speed"] * params["empty_share"])
            ship_cost += (impedance["channel"] + params["other_costs"]
                          + params["terminal_cost"])*2
            mode_cost[mode][draught] = ship_cost
    ship_cost = mode_cost["other_dry_cargo"]["4m"]
    ship_aux_cost = get_aux_cost(unit_costs,
                                 impedance,
                                 impedance_aux)
    return ship_cost + ship_aux_cost

def get_aux_cost(unit_costs: Dict[str, Dict],
                 impedance: Dict[str, numpy.ndarray],
                 impedance_aux: Dict[str, numpy.ndarray]):
    """Cheks whether auxiliary mode distance is over twice as long
    as main mode distance or if main mode mode has not been used 
    at all. In such cases, assigns inf for said OD pairs.
    Otherwise calculates actual auxiliary cost.

    Parameters
    ----------
    unit_costs : Dict[str, Dict]
        Freight mode (truck/freight_train/ship)
    impedance : Dict[str, numpy.ndarray]
        Type (time/dist/toll) : numpy 2d matrix
    impedance_aux : Dict[str, numpy.ndarray]
        Auxiliary specific Type (time/dist/toll) : numpy 2d matrix

    Returns
    ----------
    auxiliary road cost : numpy.ndarray
        impedance type cost : numpy 2d matrix
    """
    aux_cost = numpy.where(
        (impedance_aux["dist"] > (impedance["dist"]*2))
        | (impedance["dist"] == 0),
        numpy.inf,
        calc_road_cost(unit_costs, impedance_aux))
    return aux_cost