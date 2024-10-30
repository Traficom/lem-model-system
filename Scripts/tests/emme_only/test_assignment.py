#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import logging
import numpy
import pandas

import utils.log as log
import assignment.emme_assignment as ass
from datahandling.zonedata import ZoneData
from datahandling.matrixdata import MatrixData
from datahandling.resultdata import ResultsData
from tests.integration.test_data_handling import (
    TEST_DATA_PATH,
    ZONEDATA_PATH,
)
try:
    from assignment.emme_bindings.emme_project import EmmeProject
    import inro.emme.desktop.app as _app
    import inro.emme.database.emmebank as _eb
    emme_available = True
except ImportError:
    emme_available = False
except RuntimeError as ex:
    print(f'Unable to start Emme. Emme assignment tests disabled. ({ex})')
    emme_available = False

class EmmeAssignmentTest:
    """Create small EMME test network and test assignments.

    On first run, create new EMME project and database files.
    """
    def __init__(self):
        logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=logging.INFO)
        project_dir = TEST_DATA_PATH / "Results"
        log.info(str(project_dir))
        project_name = "test_assignment"
        db_dir = project_dir / project_name / "Database"
        try:
            project_path = _app.create_project(project_dir, project_name)
            db_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            project_path = project_dir / project_name / (project_name + ".emp")
        dim = {
            "scalar_matrices": 100,
            "origin_matrices": 100,
            "destination_matrices": 100,
            "full_matrices": 400,
            "scenarios": 5,
            "centroids": 20,
            "regular_nodes": 1000,
            "links": 2000,
            "turn_entries": 100,
            "transit_vehicles": 30,
            "transit_lines": 20,
            "transit_segments": 2000,
            "extra_attribute_values": 500000,
            "functions": 99,
            "operators": 5000,
            "sola_analyses": 240,
        }
        scenario_num = 19
        try:
            eb = _eb.create(db_dir / "emmebank", dim)
            eb.create_scenario(scenario_num)
            emmebank_path = eb.path
            eb.dispose()
        except RuntimeError:
            emmebank_path = None
        emme_context = EmmeProject(project_path, emmebank_path, "test")
        emme_context.import_scenario(
            project_dir.parent / "Network", scenario_num, "test",
            overwrite=True)
        self.ass_model = ass.EmmeAssignmentModel(emme_context, scenario_num)
        dist_cost = {
            "car_work": 0.12,
            "car_leisure": 0.12,
            "trailer_truck": 0.5,
            "semi_trailer": 0.4,
            "truck": 0.3,
            "van": 0.2,
        }
        self.ass_model.prepare_network(dist_cost)
        self.resultdata = ResultsData(TEST_DATA_PATH / "Results" / "assignment")
    
    def test_assignment(self):
        nr_zones = self.ass_model.nr_zones
        car_matrix = numpy.full((nr_zones, nr_zones), 10.0)
        demand = {
            "car_work": car_matrix,
            "car_leisure": car_matrix,
            "transit_work": car_matrix,
            "transit_leisure": car_matrix,
            # "car_first_mile": car_matrix,
            # "car_last_mile": car_matrix,
            "bike": car_matrix,
            "trailer_truck": car_matrix,
            "semi_trailer": car_matrix,
            "truck": car_matrix,
            "van": car_matrix,
        }
        travel_cost = {}
        self.ass_model.init_assign()
        self.test_transit_cost()
        for ap in self.ass_model.assignment_periods:
            for ass_class in demand:
                ap.set_matrix(ass_class, car_matrix)
            travel_cost[ap.name] = ap.end_assign()
        mapping = pandas.Series({
            "Helsinki": "Uusimaa",
            "Espoo": "Uusimaa",
            "Lohja": "Uusimaa",
            "Salo": "Varsinais-Suomi",
        })
        self.ass_model.aggregate_results(self.resultdata, mapping)
        self.ass_model.calc_noise(mapping)
        self.resultdata.flush()
        costs_files = MatrixData(
            TEST_DATA_PATH / "Results" / "assignment" / "Matrices")
        for time_period in travel_cost:
            for mtx_type in travel_cost[time_period]:
                zone_numbers = self.ass_model.zone_numbers
                with costs_files.open(mtx_type, time_period, zone_numbers, m='w') as mtx:
                    for ass_class in travel_cost[time_period][mtx_type]:
                        cost_data = travel_cost[time_period][mtx_type][ass_class]
                        mtx[ass_class] = cost_data

    def test_transit_cost(self):
        zdata = ZoneData(
            ZONEDATA_PATH, self.ass_model.zone_numbers, "uusimaa")
        self.ass_model.calc_transit_cost(zdata.transit_zone)

def test_freight_assignment(self):
        dist_cost = {
            "car_work": 0.12,
            "car_leisure": 0.12,
            "trailer_truck": 0.5,
            "semi_trailer": 0.4,
            "truck": 0.3,
            "van": 0.2,
        }
        purposes = ["c1", "c2"]
        self.ass_model.prepare_freight_network(dist_cost, purposes)
        temp_impedance = self.ass_model.freight_network.assign()
        nr_zones = self.ass_model.nr_zones
        demand = numpy.full((nr_zones, nr_zones), 1.0)
        for purpose in purposes:
            for mode in ["truck", "freight_train", "ship"]:
                self.ass_model.freight_network.set_matrix(mode, demand)
            self.ass_model.freight_network.save_network_volumes(purpose)
            self.ass_model.freight_network.output_traversal_matrix(
                self.resultdata.path)

if emme_available:
    em = EmmeAssignmentTest()
    em.test_assignment()
    em.test_freight_assignment()
