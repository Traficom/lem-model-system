#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import numpy
import unittest

from demand.freight import FreightModel
from models.logit import ModeDestModel
from datatypes.purpose import FreightPurpose
from datahandling.zonedata import ZoneData
from datahandling.resultdata import ResultsData


TEST_DATA_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "test_data")
METROPOLITAN_ZONES = [102, 103, 244, 1063, 1531, 2703, 2741, 6272, 6291]
PERIPHERAL_ZONES = [19071]
EXTERNAL_ZONES = [36102, 36500]


class FreightModelTest(unittest.TestCase):
    resultdata = ResultsData(os.path.join(TEST_DATA_PATH, "Results", "test"))
    zonedata = ZoneData(
        os.path.join(TEST_DATA_PATH, "Scenario_input_data", "2030_test"),
        numpy.array(METROPOLITAN_ZONES + PERIPHERAL_ZONES + EXTERNAL_ZONES))
    parameters_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "parameters", "freight")
    purposes = []
    for file_name in os.listdir(parameters_path):
        with open(os.path.join(parameters_path, file_name), 'r') as file:
            purposes.append(FreightPurpose(json.load(file), zonedata))
    mtx = numpy.arange(90, dtype=numpy.float32)
    mtx.shape = (10, 10)
    mtx[numpy.diag_indices(10)] = 0
    impedance = {
        "truck": {
            "cost": mtx,
        },
        "train": {
            "cost": mtx,
        },
    }
    for purpose in purposes:
        purpose.calc_traffic(impedance)
