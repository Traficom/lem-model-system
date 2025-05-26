#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy
import pandas
import unittest
from datahandling.zonedata import ZoneData
from models.tour_combinations import TourCombinationModel
from tests.integration.test_data_handling import ZONEDATA_PATH


INTERNAL_ZONES = [202, 1344, 1755, 2037, 2129, 2224, 2333, 2413, 2519,
                  2621, 2707, 2814, 2918, 3000, 3003, 3203, 3302, 3416,
                  3639, 3705, 3800, 4013, 4102, 4202]
EXTERNAL_ZONES = [7043, 8284, 12614, 17278, 19401, 23678]
ZONE_INDEXES = numpy.array(INTERNAL_ZONES + EXTERNAL_ZONES)


class TourCombinationModelTest(unittest.TestCase):
    def test_generation(self):
        zi = numpy.array(INTERNAL_ZONES + EXTERNAL_ZONES)
        zd = ZoneData(ZONEDATA_PATH, zi, "uusimaa")
        zd._values["hb_edu_student"] = pandas.Series(0.0, INTERNAL_ZONES)
        model = TourCombinationModel(zd)
        prob = model.calc_prob("age_50_64", False, 202)
        self.assertIs(type(prob[("hb_edu_student",)]), numpy.ndarray)
        self.assertAlmostEquals(sum(prob.values()), 1)
        prob = model.calc_prob("age_7_17", True, slice(0, 9))
        self.assertIs(type(prob[()]), pandas.core.series.Series)
        self.assertEquals(prob[("hb_edu_student", "hb_edu_student")].values.ndim, 1)
