#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import json
import numpy
import unittest
import openmatrix as omx

from datahandling.resultdata import ResultsData
from datatypes.purpose import FreightPurpose
from datahandling.zonedata import FreightZoneData
from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost
from parameters.commodity import commodity_conversion

TEST_PATH = Path(__file__).parent.parent / "test_data"
TEST_DATA_PATH = TEST_PATH / "Scenario_input_data" / "2030_test"
TEST_MATRICES = TEST_PATH / "Base_input_data" / "Matrices" / "uusimaa"
RESULT_PATH = TEST_PATH / "Results"
PARAMETERS_PATH = TEST_PATH.parent.parent / "parameters" / "freight"
ZONE_NUMBERS = [202, 1344, 1755, 2037, 2129, 2224, 2333, 2413, 2519, 2621,
                2707, 2814, 2918, 3000, 3003, 3203, 3302, 3416, 3639, 3705,
                3800, 4013, 4101, 4202, 7043, 8284, 12614, 17278, 19419, 23678]


class FreightModelTest(unittest.TestCase):

    def test_freight_model(self):      
        zonedata = FreightZoneData(
            TEST_DATA_PATH / "zonedata.gpkg", numpy.array(ZONE_NUMBERS),
            "koko_suomi")
        resultdata = ResultsData(RESULT_PATH)
        purposes = {}
        for file_name in os.listdir(PARAMETERS_PATH):
            with open(os.path.join(PARAMETERS_PATH, file_name), 'r') as file:
                commodity_params = json.load(file)
                commodity = file_name.split(".")[0]
                purposes[commodity] = FreightPurpose(commodity_params, zonedata, resultdata)
        with open(TEST_DATA_PATH / "costdata.json") as file:
            costdata = json.load(file)
        
        time_impedance = omx.open_file(TEST_MATRICES / "freight_time.omx", "r")
        dist_impedance = omx.open_file(TEST_MATRICES / "freight_dist.omx", "r")
        impedance = {
            "truck": {
                "time": numpy.array(time_impedance["truck"]),
                "dist": numpy.array(dist_impedance["truck"]),
                "toll": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            },
            "freight_train": {
                "time": numpy.array(time_impedance["freight_train"]),
                "dist": numpy.array(dist_impedance["freight_train"])
            },
            "freight_train_aux": {
                "time": numpy.array(time_impedance["freight_train_aux"]),
                "dist": numpy.array(dist_impedance["freight_train_aux"]),
                "toll": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            },
            "ship": {
                "dist": numpy.array(dist_impedance["ship"]),
                "channel": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            },
            "ship_aux": {
                "time": numpy.array(time_impedance["ship_aux"]),
                "dist": numpy.array(dist_impedance["ship_aux"]),
                "toll": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            }
        }
        for purpose_key, purpose_value in purposes.items():
            commodity_costs = costdata["freight"][commodity_conversion[purpose_key]]
            costs = {"truck": {}, "freight_train": {}, "ship": {}}
            costs["truck"]["cost"] = calc_road_cost(commodity_costs,
                                                    impedance["truck"])
            costs["freight_train"]["cost"] = calc_rail_cost(commodity_costs,
                                                            impedance["freight_train"],
                                                            impedance["freight_train_aux"])
            costs["ship"]["cost"] = calc_ship_cost(commodity_costs,
                                                   impedance["ship"],
                                                   impedance["ship_aux"])
            demand = purpose_value.calc_traffic(costs, purpose_key)
            for mode in demand:
                self.assertFalse(numpy.isnan(demand[mode]).any())
