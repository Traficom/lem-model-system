import numpy
import pandas
import unittest
import parameters
from datahandling.zonedata import BaseZoneData
from models.linear import CarDensityModel
from datahandling.resultdata import ResultsData
from tests.integration.test_data_handling import RESULTS_PATH, BASE_ZONEDATA_PATH


INTERNAL_ZONES = [102, 103, 244, 1063, 1531, 2703, 2741, 6272, 6291, 19071]
EXTERNAL_ZONES = [36102, 36500]


class LinearModelTest(unittest.TestCase):
    def test_linear_calc(self):
        resultdata = ResultsData(RESULTS_PATH)
        class Purpose:
            pass
        pur = Purpose()
        zi = numpy.array(INTERNAL_ZONES + EXTERNAL_ZONES)
        zd = BaseZoneData(BASE_ZONEDATA_PATH, zi)
        zd["time_ratio"] = pandas.Series(
            [0.9, 1.5, 1.3, 1.9, 2.0, 3.1, 1.3, 1.9, 2.0, 3.1, 0.0, 0.0],
            zi)
        zd["cost_ratio"] = pandas.Series(
            [1.1, 0.9, 0.8, 1.2, 0.5, 0.4, 1.3, 1.9, 2.0, 3.1, 0.0, 0.0],
            zi)
        pur.bounds = slice(0, 9)
        pur.zone_numbers = INTERNAL_ZONES[pur.bounds]
        bounds = slice(0, zd.nr_zones)
        model = CarDensityModel(zd, zd, bounds, resultdata)
        prediction = model.predict()
        zd["car_density"] = prediction
        self._validate(prediction)
        
    
    def _validate(self, prediction):
        self.assertIs(type(prediction), pandas.core.series.Series)
        self.assertEquals(prediction.ndim, 1)
        self.assertEquals(prediction.shape[0], 10)
        self.assertEquals(prediction.size, 10)
        self.assertNotEquals(prediction.iloc[0], 0)
        assert numpy.isfinite(prediction).all()
