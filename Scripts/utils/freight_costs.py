import numpy
from typing import Dict


def calc_road_cost(unit_cost_parameters: Dict[str, Dict],
                   distance: numpy.ndarray,
                   time: numpy.ndarray,
                   toll_cost: numpy.ndarray = 0) -> numpy.ndarray:
    mode_cost = {}
    for mode, params in unit_cost_parameters.items():
        road_cost = (time*params["time"] + distance*params["dist"]
                     + toll_cost) / params["avg_load"]
        mode_cost[mode] = ((params["terminal"]*2
                            + road_cost*params["empty_share"])
                           * params["distribution"])
    return sum(mode_cost.values())


def calc_rail_cost(rail_unit_costs: Dict[str, Dict],
                   road_unit_costs: Dict[str, Dict],
                   distance: numpy.ndarray,
                   time: numpy.ndarray,
                   aux_distance: numpy.ndarray,
                   aux_time: numpy.ndarray,
                   toll_cost: numpy.ndarray = 0) -> numpy.ndarray:
    mode_cost = {}
    for mode, params in rail_unit_costs.items():
        rail_cost = (time*params["time"] + distance*params["dist"]
                      + toll_cost) / params["avg_load"] * 2
        mode_cost[mode] = (rail_cost + params["wagon_annual"]
                           + params["terminal"]*2)
    rail_cost = mode_cost["diesel_train"]
    rail_aux_cost = get_aux_cost(road_unit_costs, distance,
                                 aux_distance, aux_time)
    return rail_cost + rail_aux_cost


def calc_ship_cost(ship_unit_costs: Dict[str, Dict],
                   road_unit_costs: Dict[str, Dict],
                   distance: numpy.ndarray,
                   aux_distance: numpy.ndarray,
                   aux_time: numpy.ndarray,
                   channel_cost: numpy.ndarray = 0) -> numpy.ndarray:
    mode_cost = {}
    for mode in ship_unit_costs:
        mode_cost[mode] = {}
        for draught, params in ship_unit_costs[mode].items():
            ship_cost = (params["time"]*distance / params["speed"]
                         * params["empty_share"])
            ship_cost += (channel_cost + params["other_costs"]
                          + params["terminal"])*2
            mode_cost[mode][draught] = ship_cost
    ship_cost = mode_cost["other_dry_cargo"]["4m"]
    ship_aux_cost = get_aux_cost(road_unit_costs, distance,
                                 aux_distance, aux_time)
    return ship_cost + ship_aux_cost

def get_aux_cost(road_unit_costs: Dict[str, Dict],
                 distance: numpy.ndarray,
                 aux_distance: numpy.ndarray,
                 aux_time: numpy.ndarray) -> numpy.ndarray:
    aux_cost = numpy.where(
        (aux_distance > (distance*2)) | (distance == 0), numpy.inf,
        calc_road_cost(road_unit_costs, aux_distance, aux_time))
    return aux_cost