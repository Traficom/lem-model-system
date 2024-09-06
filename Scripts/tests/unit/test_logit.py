#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy
import pandas
import unittest
import json
from pathlib import Path

from datahandling.zonedata import ZoneData
from models.logit import ModeDestModel
from datatypes.purpose import attempt_calibration
from datahandling.resultdata import ResultsData
from tests.integration.test_data_handling import RESULTS_PATH, BASE_ZONEDATA_PATH


METROPOLITAN_ZONES = [102, 103, 244, 1063, 1531, 2703, 2741, 6272, 6291]
PERIPHERAL_ZONES = [19071]
EXTERNAL_ZONES = [36102, 36500]
ZONE_INDEXES = numpy.array(METROPOLITAN_ZONES + PERIPHERAL_ZONES + EXTERNAL_ZONES)


class LogitModelTest(unittest.TestCase):
    def test_logit_calc(self):
        resultdata = ResultsData(RESULTS_PATH)
        class Purpose:
            pass
        pur = Purpose()
        zi = numpy.array(METROPOLITAN_ZONES + PERIPHERAL_ZONES + EXTERNAL_ZONES)
        zd = ZoneData(BASE_ZONEDATA_PATH, zi, "uusimaa")
        zd["car_users"] = pandas.Series(0.5, zd.zone_numbers)
        mtx = numpy.arange(90, dtype=numpy.float32)
        mtx.shape = (9, 10)
        mtx[numpy.diag_indices(9)] = 0
        impedance = {
            "car_work": {
                "time": mtx,
                "cost": mtx,
                "dist": mtx,
            },
            "car_leisure": {
                "time": mtx,
                "cost": mtx,
                "dist": mtx,
            },
            "car_pax": {
                "time": mtx,
                "cost": mtx,
                "dist": mtx,
            },
            "transit_work": {
                "time": mtx,
                "cost": mtx,
                "dist": mtx,
            },
            "transit_leisure": {
                "time": mtx,
                "cost": mtx,
                "dist": mtx,
            },
            "bike": {
                "dist": mtx,
            },
            "walk": {
                "dist": mtx,
            },
        }
        pur.bounds = slice(0, 9)
        pur.sub_bounds = [slice(0, 7), slice(7, 9)]
        pur.zone_numbers = METROPOLITAN_ZONES
        pur.dist = mtx
        parameters_path = Path(__file__).parents[2] / "parameters" / "demand"
        for file in parameters_path.rglob("hb_work.json"):
            parameters = json.loads(file.read_text("utf-8"))
            attempt_calibration(parameters)
            pur.name = parameters["name"]
            if ("sec_dest" not in parameters
                    and parameters["orig"] != "source"
                    and parameters["dest"] not in ("home", "source")
                    and parameters["area"] != "peripheral"):
                model = ModeDestModel(pur, parameters, zd, resultdata)
                prob = model.calc_prob(impedance)
                if parameters["dest"] in ("work"):
                    for mode in ("car_work", "transit_work", "bike", "walk"):
                        self._validate(prob[mode])
                else:
                    for mode in ("car_leisure", "transit_leisure", "bike", "walk"):
                        self._validate(prob[mode])

    def _validate(self, prob):
        self.assertIs(type(prob), numpy.ndarray)
        self.assertEquals(prob.ndim, 2)
        self.assertEquals(prob.shape[1], 9)
        self.assertNotEquals(prob[1, 0], 0)
        assert numpy.isfinite(prob).all()