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
            TEST_DATA_PATH / "freight_zonedata.gpkg", numpy.array(ZONE_NUMBERS),
            "koko_suomi")
        resultdata = ResultsData(RESULT_PATH)
        purposes = {}
        with open(TEST_DATA_PATH / "costdata.json") as file:
            costdata = json.load(file)
        for commodity in ("marita", "kalevi"):
            with open(PARAMETERS_PATH / f"{commodity}.json", 'r') as file:
                commodity_params = json.load(file)
                purposes[commodity] = FreightPurpose(commodity_params,
                                                     zonedata,
                                                     resultdata,
                                                     costdata["freight"][commodity_conversion[commodity]])

        time_impedance = omx.open_file(TEST_MATRICES / "freight_time.omx", "r")
        dist_impedance = omx.open_file(TEST_MATRICES / "freight_dist.omx", "r")
        impedance = {
            "truck": {
                "time": numpy.array(time_impedance["truck"]),
                "dist": numpy.array(dist_impedance["truck"]),
                "toll_cost": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            },
            "freight_train": {
                "time": numpy.array(time_impedance["freight_train"]),
                "dist": numpy.array(dist_impedance["freight_train"]),
                "aux_time": numpy.array(time_impedance["freight_train_aux"]),
                "aux_dist": numpy.array(dist_impedance["freight_train_aux"]),
                "toll_cost": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            },
            "ship": {
                "dist": numpy.array(dist_impedance["ship"]),
                "canal_cost": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)]),
                "aux_time": numpy.array(time_impedance["ship_aux"]),
                "aux_dist": numpy.array(dist_impedance["ship_aux"]),
                "toll": numpy.zeros([len(ZONE_NUMBERS), len(ZONE_NUMBERS)])
            }
        }
        for purpose in purposes.values():
            demand = purpose.calc_traffic(impedance)
            for mode in demand:
                self.assertFalse(numpy.isnan(demand[mode]).any())
