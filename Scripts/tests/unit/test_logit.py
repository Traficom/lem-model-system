#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import numpy
import unittest
import parameters
from datahandling.zonedata import ZoneData
from models.logit import ModeDestModel, DestModeModel
import datahandling.resultdata as result


class LogitModelTest(unittest.TestCase):
    def test_logit_calc(self):
        result.set_path("test")
        class Purpose:
            pass
        pur = Purpose()
        pur.bounds = (0, 4)
        zd = ZoneData("2016_test")
        mtx = numpy.arange(24)
        mtx.shape = (4, 6)
        mtx[numpy.diag_indices(4)] = 0
        impedance = {
            "car": {
                "time": mtx,
                "cost": mtx,
                "dist": mtx,
            },
            "transit": {
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
        for i in ("hw", "hc", "hu", "hs", "ho", "wo", "oo"):
            pur.name = i
            model = ModeDestModel(zd, pur)
            prob = model.calc_prob(impedance)
            for mode in ("car", "transit", "bike", "walk"):
                self._validate(prob[mode])
        pur.name = "so"
        model = DestModeModel(zd, pur)
        prob = model.calc_prob(impedance)
        for mode in ("car", "transit", "bike", "walk"):
            self._validate(prob[mode])
        for i in ("hwp", "hop", "oop"):
            pur.name = i
            model = ModeDestModel(zd, pur)
            prob = model.calc_prob(impedance)
            for mode in ("car", "transit"):
                self._validate(prob[mode])
    
    def _validate(self, prob):
        self.assertIs(type(prob), numpy.ndarray)
        self.assertEquals(prob.ndim, 2)
        self.assertEquals(prob.shape[1], 4)
        self.assertNotEquals(prob[0, 1], 0)
        assert numpy.isfinite(prob).all()