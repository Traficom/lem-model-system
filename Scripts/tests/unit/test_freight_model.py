#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import numpy
import unittest

from datatypes.purpose import FreightPurpose
from datahandling.zonedata import ZoneData
from datahandling.resultdata import ResultsData
from assignment.emme_bindings.emme_project import EmmeProject
from assignment.emme_assignment import EmmeAssignmentModel

from typing import Dict

TEST_DATA_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "test_data")
METROPOLITAN_ZONES = numpy.loadtxt(
    os.path.join(TEST_DATA_PATH, "Scenario_input_data",
                 "2030_test", "freight_zones.csv"))
MODEL_TYPE = "dest_mode"
ESTIM_TYPE = "attr"

class FreightModelTest(unittest.TestCase):

    def test_freight_model(self):

        def read_freight_costdata():
            path = os.path.join(TEST_DATA_PATH, "Scenario_input_data", "2030_test")
            freight_costdata = {
                "truck": "freight_truck_costs.json",
                "freight_train": "freight_train_costs.json",
                "ship": "freight_ship_costs.json"}
            for k,v in freight_costdata.items():
                with open(path + "\\" + v) as f:
                   freight_costdata[k] = json.load(f)
            return freight_costdata

        def calc_road_cost(purpose_key: str, road_json: Dict[str, Dict],
                           distance: numpy.ndarray, time: numpy.ndarray,
                           toll_cost: numpy.ndarray = 0) -> numpy.ndarray:
            road_json = road_json[purpose_key]
            mode_cost = {}
            for mode in road_json.keys():
                mdata = road_json[mode]
                time_cost = time * mdata["time_based_cost"]
                dist_cost = distance * mdata["distance_based_cost"]
                road_cost = (time_cost + dist_cost + toll_cost) / mdata["average_load"]
                mode_cost[mode] = (road_cost + (mdata["terminal_cost"] * 2)\
                    + (road_cost * mdata["empty_share"])) * mdata["distribution"]
            road_total_cost = sum(mode_cost.values())
            return road_total_cost

        def calc_rail_cost(purpose_key: str, cost_json: Dict[str, Dict],
                           distance: numpy.ndarray, aux_distance: numpy.ndarray,
                           aux_time: numpy.ndarray, toll_cost: numpy.ndarray = 0) -> numpy.ndarray:
            rail_json = cost_json["freight_train"][purpose_key]
            speed = cost_json["freight_train"]["speed"]
            empty_share = cost_json["freight_train"]["empty_share"]
            mode_cost = {}
            for mode in rail_json.keys():
                mdata = rail_json[mode]
                time_cost =  mdata["time_based_cost"] * distance / speed[mode] * empty_share
                dist_cost = distance * mdata["distance_based_cost"] * empty_share
                rail_cost = ((time_cost + dist_cost + toll_cost) / mdata["average_load"]\
                    + mdata["wagon_yearly_cost"])
                mode_cost[mode] = rail_cost + (mdata["terminal_cost"] * 2)
            rail_cost = mode_cost["diesel_train"]
            rail_aux_cost = numpy.where((aux_distance > (distance + aux_distance) / 2)\
                | (aux_distance == (distance + aux_distance)),
                numpy.inf,
                calc_road_cost(purpose_key, cost_json["truck"],
                               aux_distance, aux_time))
            return rail_cost + rail_aux_cost

        def calc_ship_cost(purpose_key: str, cost_json: Dict[str, Dict],
                           distance: numpy.ndarray, aux_distance: numpy.ndarray,
                           aux_time: numpy.ndarray, channel_cost: numpy.ndarray = 0) -> numpy.ndarray:
            ship_json = cost_json["ship"][purpose_key]
            empty_share = cost_json["ship"]["empty_share"]
            mode_cost = {}
            for mode in ship_json.keys():
                for draught in ship_json[mode]:
                    mdata = ship_json[mode][draught]
                    time_cost = mdata["time_based_cost"] * (distance / (mdata["speed"]))
                    channel_cost = mdata["other_costs"]
                    ship_cost = time_cost + channel_cost + (mdata["terminal_cost"] * 2)
                    ship_cost += time_cost * empty_share
                    drdict = {draught: ship_cost}
                mode_cost[mode] = drdict
            ship_cost = mode_cost["other_dry_cargo"]["4m"]
            ship_aux_cost = numpy.where((aux_distance > (distance + aux_distance) / 2)\
                | (aux_distance == (distance + aux_distance)),
                numpy.inf,
                calc_road_cost(purpose_key, cost_json["truck"],
                               aux_distance, aux_time))
            return ship_cost + ship_aux_cost

        resultdata = ResultsData(os.path.join(TEST_DATA_PATH, "Results",
                                              "test", "freight", MODEL_TYPE))
        zonedata = ZoneData(
            os.path.join(TEST_DATA_PATH, "Scenario_input_data", "2030_test"),
            numpy.array(METROPOLITAN_ZONES),
            "freight_zones.zmp"
            )
        parameters_path = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), "..", "..", "parameters",
                "freight", MODEL_TYPE)
        purposes = {}
        for file_name in os.listdir(parameters_path):
            if file_name.endswith(".json"):
                with open(os.path.join(parameters_path, file_name), 'r') as file:
                    fname = file_name.split("_")[1]
                    purposes[fname] = FreightPurpose(json.load(file), zonedata,
                                                    resultdata)
        ass_model = EmmeAssignmentModel(
            EmmeProject("C:\\emmeproj\\freight_testing\\freight_testing.emp"), first_scenario_id=11)
        ass_model.prepare_freight_network(zonedata.car_dist_cost)
        temp_impedance = ass_model.freight_network.assign()
        freight_costdata = read_freight_costdata()
        demand_list = {}
        for purpose_key, purpose_value in purposes.items():
            impedance = {
                "truck": {
                    "cost": calc_road_cost(purpose_key,
                                           freight_costdata["truck"],
                                           temp_impedance["time"]["truck"],
                                           temp_impedance["dist"]["truck"])
                },
                "freight_train": {
                    "cost": calc_rail_cost(purpose_key,
                                           freight_costdata,
                                           temp_impedance["dist"]["freight_train"],
                                           temp_impedance["aux_dist"]["freight_train"],
                                           temp_impedance["aux_time"]["freight_train"])
                },
                "ship": {
                    "cost": calc_ship_cost(purpose_key,
                                           freight_costdata,
                                           temp_impedance["dist"]["ship"],
                                           temp_impedance["aux_dist"]["ship"],
                                           temp_impedance["aux_time"]["ship"])
                },
            }
            demand = purpose_value.calc_traffic(impedance)
            for mode in demand:
                ass_model.freight_network.set_matrix(mode, demand[mode])
            demand_list[purpose_key] = demand
        ass_model.freight_network.assign()

test = FreightModelTest()
test.test_freight_model()
