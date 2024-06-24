import unittest
import numpy
from pathlib import Path

import utils.log as log
from modelsystem import ModelSystem, AgentModelSystem
from assignment.mock_assignment import MockAssignmentModel
from datahandling.matrixdata import MatrixData
from datatypes.demand import Demand
from tests.integration.test_data_handling import (
    TEST_DATA_PATH,
    RESULTS_PATH,
    ZONEDATA_PATH,
    BASE_ZONEDATA_PATH,
    BASE_MATRICES_PATH,
)


class Config():
    log_format = None
    log_level = "DEBUG"
    scenario_name = "TEST"
    results_path = TEST_DATA_PATH / "Results"


class ModelTest(unittest.TestCase):
    
    def test_models(self):
        print("Testing assignment..")
        log.initialize(Config())
        ass_model = MockAssignmentModel(MatrixData(
            RESULTS_PATH / "Matrices" / "uusimaa"))
        model = ModelSystem(
            ZONEDATA_PATH, BASE_ZONEDATA_PATH, BASE_MATRICES_PATH,
            RESULTS_PATH, ass_model, "uusimaa")
        impedance = model.assign_base_demand()
        for ap in ass_model.assignment_periods:
            tp = ap.name
            print("Validating impedance")
            self.assertEqual(3, len(impedance[tp]))
            self.assertIsNotNone(impedance[tp]["time"])
            self.assertIsNotNone(impedance[tp]["cost"])
            self.assertIsNotNone(impedance[tp]["dist"])
            
        print("Adding demand and assigning")
        impedance = model.run_iteration(impedance)

        self.assertEquals(len(ass_model.assignment_periods), len(impedance))
        self._validate_impedances(impedance["aht"])
        self._validate_impedances(impedance["pt"])
        self._validate_impedances(impedance["iht"])

        # Check that model result does not change
        self.assertAlmostEquals(
            model.mode_share[0]["car_work"] + model.mode_share[0]["car_leisure"],
            0.25467787853321716)
        
        print("Model system test done")
    
    def _validate_impedances(self, impedances):
        self.assertIsNotNone(impedances)
        self.assertIs(type(impedances), dict)
        self.assertEquals(len(impedances), 3)
        self.assertIsNotNone(impedances["time"])
        self.assertIsNotNone(impedances["cost"])
        self.assertIsNotNone(impedances["dist"])
        self.assertIs(type(impedances["time"]), dict)
        self.assertEquals(len(impedances["time"]), 6)
        self.assertIsNotNone(impedances["time"]["transit_work"])
        self.assertIs(type(impedances["time"]["transit_work"]), numpy.ndarray)
        self.assertEquals(impedances["time"]["transit_work"].ndim, 2)
        self.assertEquals(len(impedances["time"]["transit_work"]), 12)

    def _validate_demand(self, demand):
        self.assertIsNotNone(demand)
        self.assertIsNotNone(demand)
        self.assertIsInstance(demand, Demand)
        self.assertIs(type(demand.matrix), numpy.ndarray)
        self.assertEquals(demand.matrix.ndim, 2)
        self.assertEquals(demand.matrix.shape[1], 6)
