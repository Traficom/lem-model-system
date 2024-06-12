import numpy
from typing import Dict


def calc_road_cost(unit_cost_parameters: Dict[str, Dict],
                   distance: numpy.ndarray,
                   time: numpy.ndarray,
                   toll_cost: numpy.ndarray = 0) -> numpy.ndarray:
    mode_cost = {}
    for mode, parameters in unit_cost_parameters.items():
        time_cost = time * parameters["time_based_cost"]
        dist_cost = distance * parameters["distance_based_cost"]
        road_cost = (time_cost+dist_cost+toll_cost) / parameters["average_load"]
        mode_cost[mode] = ((parameters["terminal_cost"]*2
                            + road_cost*parameters["empty_share"])
                           * parameters["distribution"])
    road_total_cost = sum(mode_cost.values())
    return road_total_cost


def calc_rail_cost(rail_unit_costs: Dict[str, Dict],
                   road_unit_costs: Dict[str, Dict],
                   distance: numpy.ndarray,
                   time: numpy.ndarray,
                   aux_distance: numpy.ndarray,
                   aux_time: numpy.ndarray,
                   toll_cost: numpy.ndarray = 0) -> numpy.ndarray:
    mode_cost = {}
    for mode, parameters in rail_unit_costs.items():
        time_cost =  parameters["time_based_cost"] * time
        dist_cost = distance * parameters["distance_based_cost"]
        rail_cost = ((time_cost+dist_cost+toll_cost)
                     / parameters["average_load"]*2
                     + parameters["wagon_yearly_cost"])
        mode_cost[mode] = rail_cost + (parameters["terminal_cost"]*2)
    rail_cost = mode_cost["diesel_train"]
    rail_aux_cost = numpy.where(
        (aux_distance > (distance*2)) | (distance == 0), numpy.inf,
        calc_road_cost(road_unit_costs, aux_distance, aux_time))
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
        for draught, parameters in ship_unit_costs[mode].items():
            time_cost = (parameters["time_based_cost"] * distance
                         / parameters["speed"])
            ship_cost = time_cost * parameters["empty_share"]
            time_cost + channel_cost + parameters["terminal_cost"]*2
            ship_cost += (channel_cost + parameters["other_costs"]
                          + parameters["terminal_cost"])*2
            mode_cost[mode][draught] = ship_cost
    ship_cost = mode_cost["other_dry_cargo"]["4m"]
    ship_aux_cost = numpy.where(
        (aux_distance > (distance*2)) | (distance == 0), numpy.inf,
        calc_road_cost(road_unit_costs, aux_distance, aux_time))
    return ship_cost + ship_aux_cost
