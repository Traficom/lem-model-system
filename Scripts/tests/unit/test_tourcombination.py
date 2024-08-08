#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy
import pandas
import unittest
from datahandling.zonedata import BaseZoneData
from models.tour_combinations import TourCombinationModel
from tests.integration.test_data_handling import BASE_ZONEDATA_PATH
from utils.read_csv_file import read_mapping


METROPOLITAN_ZONES = [102, 103, 244, 1063, 1531, 2703, 2741, 6272, 6291]
PERIPHERAL_ZONES = [19071]
EXTERNAL_ZONES = [36102, 36500]
ZONE_INDEXES = numpy.array(METROPOLITAN_ZONES + PERIPHERAL_ZONES + EXTERNAL_ZONES)


class TourCombinationModelTest(unittest.TestCase):
    def test_generation(self):
        zi = numpy.array(METROPOLITAN_ZONES + PERIPHERAL_ZONES + EXTERNAL_ZONES)
        zone_mapping = read_mapping(BASE_ZONEDATA_PATH / "zones_uusimaa.tsv", ZONE_INDEXES)
        zd = BaseZoneData(BASE_ZONEDATA_PATH, zi, zone_mapping)
        zd._values["hb_edu_higher_t"] = pandas.Series(0.0, METROPOLITAN_ZONES)
        model = TourCombinationModel(zd)
        prob = model.calc_prob("age_50-64", False, 102)
        self.assertIs(type(prob[("hb_edu_higher",)]), numpy.ndarray)
        self.assertAlmostEquals(sum(prob.values()), 1)
        prob = model.calc_prob("age_7-17", True, slice(0, 9))
        self.assertIs(type(prob[()]), pandas.core.series.Series)
        self.assertEquals(prob[("hb_edu_higher", "hb_edu_higher")].values.ndim, 1)
