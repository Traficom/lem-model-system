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

        def calc_road_cost(purpose_key, road_json, distance, time) -> numpy.array:
            comm_info = road_json["commodity_spec"][str(purpose_key)]
            mode_cost = {}
            for mode in comm_info["veh_info"]:
                mdata = road_json["vehicle_spec"][mode]
                vdata = comm_info["veh_info"][mode]
                # Pituus kustannukset
                distance_cost = vdata["distribution"] * distance \
                    * (mdata["fuel_cost"] + mdata["other_cost"]) \
                    * (1 + comm_info["empty_share"])
                # Ajoajan kustannukset
                drive_time_cost = time * (mdata["capital_cost"] + mdata["work_cost"]) \
                    * (1 + comm_info["empty_share"])
                # Kuormaus ja purkuajan kustannukset
                loading_cost = comm_info["loading_time"] \
                    * (mdata["capital_cost"] + mdata["work_cost"])
                # Eräkoko
                batch_size = mdata["capacity"] * vdata["fill_rate"]
                mode_cost[mode] = (distance_cost + drive_time_cost + loading_cost) / batch_size
            road_total_cost = sum(mode_cost.values())
            return road_total_cost

        def calc_rail_cost(purpose_key, road_json, distance, aux_distance, aux_time) -> numpy.array:
            if purpose_key == "2":
                rail_cost = (0.0166 * distance) + 7.994
            elif purpose_key in ("4", "8"):
                rail_cost = (-0.000005 * distance ** 2) + (0.0174 * distance) + 3.282
            elif purpose_key in ("7", "9", "10", "11"):
                rail_cost = (-0.00001 * distance ** 2) + (0.0293 * distance) + 6.5205
            else:
                rail_cost = (-0.00003 * distance ** 2) + (0.058238 * distance) + 14.618045
            rail_aux_cost = calc_road_cost(purpose_key, road_json,
                                           aux_distance, aux_time)
            rail_total_cost = rail_cost + rail_aux_cost
            return rail_total_cost

        def calc_ship_cost(purpose_key, road_json, distance, aux_distance, aux_time) -> numpy.array:
            ship_cost = 0.00811 * distance + 11.04274
            ship_aux_cost = calc_road_cost(purpose_key, road_json,
                                           aux_distance, aux_time)
            ship_total_cost = ship_cost + ship_aux_cost
            return ship_total_cost

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
                                           freight_costdata["truck"],
                                           temp_impedance["dist"]["freight_train"],
                                           temp_impedance["aux_dist"]["freight_train"],
                                           temp_impedance["aux_time"]["freight_train"])
                },
                "ship": {
                    "cost": calc_ship_cost(purpose_key,
                                           freight_costdata["truck"],
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
