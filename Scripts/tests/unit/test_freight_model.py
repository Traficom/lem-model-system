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
from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost


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
        ass_model.prepare_freight_network(zonedata.car_dist_cost, list(purposes))
        temp_impedance = ass_model.freight_network.assign()
        freight_costdata = read_freight_costdata()
        demand_list = {}
        for purpose_key, purpose_value in purposes.items():
            impedance = {
                "truck": {
                    "cost": calc_road_cost(freight_costdata["truck"][purpose_key],
                                           temp_impedance["time"]["truck"],
                                           temp_impedance["dist"]["truck"])
                },
                "freight_train": {
                    "cost": calc_rail_cost(freight_costdata["freight_train"][purpose_key],
                                           freight_costdata["truck"][purpose_key],
                                           freight_costdata["freight_train"]["empty_share"],
                                           temp_impedance["dist"]["freight_train"],
                                           temp_impedance["time"]["freight_train"],
                                           temp_impedance["aux_dist"]["freight_train"],
                                           temp_impedance["aux_time"]["freight_train"])
                },
                "ship": {
                    "cost": calc_ship_cost(freight_costdata["ship"][purpose_key],
                                           freight_costdata["truck"][purpose_key],
                                           freight_costdata["ship"]["empty_share"],
                                           temp_impedance["dist"]["ship"],
                                           temp_impedance["aux_dist"]["ship"],
                                           temp_impedance["aux_time"]["ship"])
                },
            }
            demand = purpose_value.calc_traffic(impedance)
            for mode in demand:
                ass_model.freight_network.set_matrix(mode, demand[mode])
            demand_list[purpose_key] = demand
            ass_model.freight_network.save_network_volumes(purpose_key)

test = FreightModelTest()
test.test_freight_model()
