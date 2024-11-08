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
            "full_matrices": 9999,
            "scenarios": 5,
            "centroids": 30,
            "regular_nodes": 2000,
            "links": 6000,
            "turn_entries": 100,
            "transit_vehicles": 35,
            "transit_lines": 30,
            "transit_segments": 700,
            "extra_attribute_values": 1100000,
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
        self.long_dist_model = ass.EmmeAssignmentModel(
            emme_context, scenario_num, use_free_flow_speeds=True,
            time_periods=["vrk"])
        dist_cost = {
            "car_work": 0.12,
            "car_leisure": 0.12,
            "trailer_truck": 0.5,
            "semi_trailer": 0.4,
            "truck": 0.3,
            "van": 0.2,
        }
        self.ass_model.prepare_network(dist_cost)
        self.long_dist_model.prepare_network(dist_cost)
        self.resultdata = ResultsData(TEST_DATA_PATH / "Results" / "assignment")
    
    def test_assignment(self):
        nr_zones = self.ass_model.nr_zones
        car_matrix = numpy.full((nr_zones, nr_zones), 10.0)
        demand = {
            "car_work": car_matrix,
            "car_leisure": car_matrix,
            "transit_work": car_matrix,
            "transit_leisure": car_matrix,
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
            "Vantaa": "Uusimaa",
            "Kauniainen": "Uusimaa",
            "Hyvinkaa": "Uusimaa",
            "Lohja": "Uusimaa",
            "Hameenlinna": "Kanta-Hame",
            "Tampere": "Pirkanmaa",
            "Turku": "Varsinais-Suomi",
            "Jyvaskyla": "Keski-Suomi",
            "Kotka": "Kymenlaakso",
            "Lahti": "Paijat-Hame"
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

    def test_park_and_ride(self):
        nr_zones = self.ass_model.nr_zones
        car_matrix = numpy.full((nr_zones, nr_zones), 10.0)
        ass_classes = [
            "car_work",
            "car_leisure",
            "train",
            "long_d_bus",
            "airplane",
            "j_first_mile",
            "j_first_taxi",
            "e_first_mile",
            "l_first_mile",
        ]
        demand = {ass_class: car_matrix for ass_class in ass_classes}
        for ap in self.long_dist_model.assignment_periods:
            for ass_class in demand:
                ap.set_matrix(ass_class, car_matrix)
            ap.assign_trucks_init()
            ap.end_assign()
            ap.transit_results_links_nodes()

    def test_transit_cost(self):
        fares = pandas.DataFrame({
            0: {
                "firstb": 2.0,
                "dist": 0.1
            },
            1: {
                "firstb": 3.0,
                "dist": 0.2
            },
            2: {
                "firstb": 5.0,
                "dist": 0.1
            },
            3: {
                "firstb": 70.0,
                "dist": 0.3
            },
            4: {
                "firstb": 0.0,
                "dist": 0.1
            }
        })
        self.ass_model.calc_transit_cost(fares)

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
    em.test_park_and_ride()
    em.test_freight_assignment()
