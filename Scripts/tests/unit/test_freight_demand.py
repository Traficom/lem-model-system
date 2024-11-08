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
from datahandling.zonedata import ZoneData
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
        zonedata = ZoneData(TEST_DATA_PATH / "zonedata.gpkg", numpy.array(ZONE_NUMBERS), "koko_suomi")
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
        for purpose_key, purpose_value in purposes.items():
            commodity_costs = costdata["freight"][commodity_conversion[purpose_key]]
            impedance = {
                "truck": {
                    "cost": calc_road_cost(commodity_costs["truck"],
                                           numpy.array(dist_impedance["truck"]),
                                           numpy.array(time_impedance["truck"]))
                },
                "freight_train": {
                    "cost": calc_rail_cost(commodity_costs["freight_train"],
                                           commodity_costs["truck"],
                                           numpy.array(dist_impedance["freight_train"]),
                                           numpy.array(time_impedance["freight_train"]),
                                           numpy.array(dist_impedance["freight_train_aux"]),
                                           numpy.array(time_impedance["freight_train_aux"]))
                },
                "ship": {"cost": calc_ship_cost(commodity_costs["ship"],
                                                commodity_costs["truck"],
                                                numpy.array(dist_impedance["ship"]),
                                                numpy.array(dist_impedance["ship_aux"]),
                                                numpy.array(time_impedance["ship_aux"]))}
            }
            demand = purpose_value.calc_traffic(impedance, purpose_key)
            for mode in demand:
                self.assertFalse(numpy.isnan(demand[mode]).any())
