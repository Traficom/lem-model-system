import unittest
import pandas
import os
import numpy
from pathlib import Path

import utils.log as log
from datahandling.zonedata import ZoneData
from datahandling.matrixdata import MatrixData
import parameters.assignment as param
from lem import BASE_ZONEDATA_FILE


TEST_DATA_PATH = Path(__file__).parent.parent / "test_data"
RESULTS_PATH = TEST_DATA_PATH / "Results" / "test"
ZONEDATA_PATH = TEST_DATA_PATH / "Scenario_input_data" / "2030_test" / "zonedata.gpkg"
COSTDATA_PATH = TEST_DATA_PATH / "Scenario_input_data" / "2030_test" / "costdata.json"
BASE_ZONEDATA_PATH = TEST_DATA_PATH / "Base_input_data" / BASE_ZONEDATA_FILE
BASE_MATRICES_PATH = TEST_DATA_PATH / "Base_input_data" / "Matrices"
INTERNAL_ZONES = [
    202, 1344, 1755, 2037, 2129, 2224, 2333, 2413, 2519, 2621, 2707, 2814, 2918,
    3000, 3003, 3203, 3302, 3416, 3639, 3705, 3800, 4013, 4101, 4202]
EXTERNAL_ZONES = [7043, 8284, 12614, 17278, 19419, 23678]
ZONE_INDEXES = numpy.array(INTERNAL_ZONES + EXTERNAL_ZONES)

# Integration tests for validating that we can read the matrices from OMX
#  and CSV files correctly. Assumes that the matrix is fixed and the
# values don't change throughout the project.

class Config():
    log_format = None
    log_level = "DEBUG"
    scenario_name = "TEST"
    results_path = TEST_DATA_PATH / "Results"

class MatrixDataTest(unittest.TestCase):

    def test_constructor(self):
        log.initialize(Config())
        m = MatrixData(BASE_MATRICES_PATH / "uusimaa")
        # Verify that the base folder exists
        self.assertTrue(os.path.isdir(m.path))

    def test_matrix_operations(self):
        log.initialize(Config())
        m = MatrixData(BASE_MATRICES_PATH / "uusimaa")
        MATRIX_TYPES = ["demand"]
        for matrix_type in MATRIX_TYPES:
            print("validating matrix type", matrix_type)
            self._validate_matrix_operations(m, matrix_type)

    def _validate_matrix_operations(self, matrix_data, matrix_type):
        emme_scenarios = ["aht", "pt", "iht"]
        expanded_zones = numpy.insert(ZONE_INDEXES, 3, 8)
        for key in emme_scenarios:
            print("Opening matrix for time period", key)
            with matrix_data.open(matrix_type, key, expanded_zones) as mtx:
                for ass_class in param.simple_transport_classes:
                    a = mtx[ass_class]


class ZoneDataTest(unittest.TestCase):

    def _get_freight_data_2016(self):
        zdata = ZoneData(BASE_ZONEDATA_PATH, ZONE_INDEXES)
        df = zdata.get_freight_data()
        self.assertIsNotNone(df)
        return df

    def test_csv_file_read(self):
        zdata2016 = ZoneData(BASE_ZONEDATA_PATH, ZONE_INDEXES, "uusimaa")
        self.assertIsNotNone(zdata2016["population"])
        self.assertIsNotNone(zdata2016["workplaces"])

        zdata2030 = ZoneData(ZONEDATA_PATH, ZONE_INDEXES, "uusimaa")
        self.assertIsNotNone(zdata2030["population"])
        self.assertIsNotNone(zdata2030["workplaces"])

        self.assertEquals(
            len(zdata2016["population"]), len(zdata2030["population"]))
        self.assertEquals(
            len(zdata2016["workplaces"]), len(zdata2030["workplaces"]))
        # Assert that data content is a bit different so we know we're
        # not reading the same file all over again
        self.assertFalse(
            zdata2016["population"].equals(zdata2030["population"]))
        self.assertFalse(
            zdata2016["workplaces"].equals(zdata2030["workplaces"]))
