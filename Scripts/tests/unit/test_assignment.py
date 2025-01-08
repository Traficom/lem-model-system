#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import unittest
import numpy
import pandas
from pathlib import Path

from utils.validate_network import validate
from assignment.emme_bindings.mock_project import MockProject
from assignment.emme_assignment import EmmeAssignmentModel
from datahandling.resultdata import ResultsData
from tests.integration.test_data_handling import TEST_DATA_PATH, RESULTS_PATH


class EmmeAssignmentTest(unittest.TestCase):
    def setUp(self):
        self.context = MockProject()
        scenario_dir = TEST_DATA_PATH / "Network"
        self.scenario_id = 19
        self.context.import_scenario(scenario_dir, self.scenario_id, "test")
        self.dist_cost = {
            "car_work": 0.12,
            "car_leisure": 0.12,
            "trailer_truck": 0.5,
            "semi_trailer": 0.4,
            "truck": 0.3,
            "van": 0.2,
        }

    def test_assignment(self):
        firstb_single = (2, 3, 5, 70, 0, 1.5)
        dist_single = (0.1, 0.2, 0.1, 0.3, 0.1, 0.2)
        fares = pandas.DataFrame(
            {i: {"firstb_single": firstb_single[i],
                 "dist_single": dist_single[i]}
             for i in range(0, len(firstb_single))})
        validate(
            self.context.modeller.emmebank.scenario(
                self.scenario_id).get_network())
        ass_model = EmmeAssignmentModel(
            self.context, self.scenario_id, use_stored_speeds=True)
        ass_model.prepare_network(self.dist_cost)
        ass_model.calc_transit_cost(fares)
        nr_zones = ass_model.nr_zones
        car_matrix = numpy.arange(nr_zones**2).reshape(nr_zones, nr_zones)
        demand = [
            "car_work",
            "car_leisure",
            "transit_work",
            "transit_leisure",
            # "car_first_mile",
            # "car_last_mile",
            "bike",
            "trailer_truck",
            "semi_trailer",
            "truck",
            "van",
        ]
        ass_model.init_assign()
        ass_model.beeline_dist
        for ap in ass_model.assignment_periods:
            for ass_class in demand:
                ap.set_matrix(
                    ass_class, car_matrix)
            ap.assign_trucks_init()
            ap.assign(demand + ["car_pax"])
            ap.end_assign()
        resultdata = ResultsData(RESULTS_PATH)
        mapping = pandas.Series({
            "Helsinki": "Uusimaa",
            "Espoo": "Uusimaa",
            "Lohja": "Uusimaa",
            "Salo": "Varsinais-Suomi",
        })
        ass_model.aggregate_results(resultdata, mapping)
        ass_model.calc_noise(mapping)
        resultdata.flush()

    def test_freight_assignment(self):
        ass_model = EmmeAssignmentModel(self.context, self.scenario_id)
        ass_model.prepare_freight_network(self.dist_cost, ["c1", "c2"])
        ass_model.freight_network.assign()
        ass_model.freight_network.save_network_volumes("c1")
