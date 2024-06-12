#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import numpy
import unittest
import openmatrix as omx

from datatypes.purpose import FreightPurpose
from datahandling.zonedata import BaseZoneData
from datahandling.zonedata import ZoneData
from datahandling.resultdata import ResultsData
from assignment.emme_bindings.emme_project import EmmeProject
from assignment.emme_assignment import EmmeAssignmentModel
from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost


TEST_DATA_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "test_data")
ZONE_NUMBERS = numpy.loadtxt(
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
        wd = os.path.join(TEST_DATA_PATH, "Scenario_input_data", "2030_test")
        resultdata = ResultsData(os.path.join(TEST_DATA_PATH, "Results",
                                              "test", "freight", MODEL_TYPE))
        basezonedata = BaseZoneData(
            wd, numpy.array(ZONE_NUMBERS), "koko_suomi_kunta.zmp")
        zonedata = ZoneData(
            wd, numpy.array(ZONE_NUMBERS), basezonedata.aggregations, "koko_suomi_kunta.zmp")
        parameters_path = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), "..", "..", "parameters",
                "freight", MODEL_TYPE)
        purposes = {}
        with open(os.path.join(wd, "comm_finage_conversion.json")) as f:
            finage_comms = json.load(f)
        for file_name in os.listdir(parameters_path):
            if file_name.endswith(".json"):
                with open(os.path.join(parameters_path, file_name), 'r') as file:
                    comm_params = json.load(file)
                    comm_names = finage_comms[file_name.split("_")[0]]
                    for comm in comm_names:
                        purposes[comm] = FreightPurpose(comm_params, zonedata,
                                                        resultdata)
        ass_model = EmmeAssignmentModel(
            EmmeProject("C:\\emmeproj\\freight_testing\\freight_testing.emp"), first_scenario_id=11)
        ass_model.prepare_freight_network(zonedata.car_dist_cost, list(purposes))
        temp_impedance = ass_model.freight_network.assign()
        freight_costdata = read_freight_costdata()
        omx_file = omx.open_file(wd + "\\freight_demand_tons_year.omx", "w")
        omx_file.create_mapping("zone_number", ZONE_NUMBERS)
        for purpose_key, purpose_value in purposes.items():
            impedance = {
                "truck": {
                    "cost": calc_road_cost(freight_costdata["truck"][purpose_key],
                                           temp_impedance["dist"]["truck"],
                                           temp_impedance["time"]["truck"])
                },
                "freight_train": {
                    "cost": calc_rail_cost(freight_costdata["freight_train"][purpose_key],
                                           freight_costdata["truck"][purpose_key],
                                           temp_impedance["dist"]["freight_train"],
                                           temp_impedance["time"]["freight_train"],
                                           temp_impedance["aux_dist"]["freight_train"],
                                           temp_impedance["aux_time"]["freight_train"])
                },
                "ship": {
                    "cost": calc_ship_cost(freight_costdata["ship"][purpose_key],
                                           freight_costdata["truck"][purpose_key],
                                           temp_impedance["dist"]["ship"],
                                           temp_impedance["aux_dist"]["ship"],
                                           temp_impedance["aux_time"]["ship"])
                },
            }
            demand = purpose_value.calc_traffic(impedance, purpose_key)
            for mode in demand:
                omx_file[f"{purpose_key}_{mode}"] = demand[mode]
                #ass_model.freight_network.set_matrix(mode, demand[mode])
            #ass_model.freight_network.save_network_volumes(purpose_key)

test = FreightModelTest()
test.test_freight_model()
