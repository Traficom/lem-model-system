import unittest

import logging
import os
import numpy
from assignment.mock_assignment import MockAssignmentModel
import assignment.departure_time as dt
from datahandling.zonedata import ZoneData
from datahandling.matrixdata import MatrixData
from demand.freight import FreightModel
from demand.trips import DemandModel
from demand.external import ExternalModel
from transform.impedance_transformer import ImpedanceTransformer
import parameters

class ModelTest(unittest.TestCase):
    
    def test_models(self):
        print("Testing assignment..")

        zdata_base = ZoneData("2016")
        zdata_forecast = ZoneData("2030")
        basematrices = MatrixData("base")
        dm = DemandModel(zdata_forecast)
        fm = FreightModel(zdata_base, zdata_forecast, basematrices)
        trucks = fm.calc_freight_traffic("truck")
        trailer_trucks = fm.calc_freight_traffic("trailer_truck")
        em = ExternalModel(basematrices, zdata_forecast)
        costs = MatrixData("2016")
        ass_model = MockAssignmentModel(costs)
        dtm = dt.DepartureTimeModel(ass_model.nr_zones)
        imptrans = ImpedanceTransformer()
        ass_classes = dict.fromkeys(parameters.emme_mtx["demand"].keys())

        self.assertEqual(7, len(ass_classes))

        impedance = {}
        for tp in parameters.emme_scenario:
            base_demand = {}
            basematrices.open_file("demand", tp)
            for ass_class in ass_classes:
                base_demand[ass_class] = basematrices.get_data(ass_class)
            basematrices.close()
            ass_model.assign(tp, base_demand)
            if tp == "aht":
                ass_model.calc_transit_cost(0)
            impedance[tp] = ass_model.get_impedance()
            print("Validating impedance")
            self.assertEqual(3, len(impedance[tp]))
            self.assertIsNotNone(impedance[tp]["time"])
            self.assertIsNotNone(impedance[tp]["cost"])
            self.assertIsNotNone(impedance[tp]["dist"])
            
        print("Adding demand and assigning")

        dtm.add_demand("freight", "truck", trucks)
        dtm.add_demand("freight", "trailer_truck", trailer_trucks)
        for purpose in dm.tour_purposes:
            purpose_impedance = imptrans.transform(purpose, impedance)
            if purpose.name == "hoo":
                l, u = purpose.bounds
                nr_zones = u - l
                purpose.generate_tours()
                for mode in purpose.model.dest_choice_param:
                    for i in xrange(0, nr_zones):
                        demand = purpose.distribute_tours(mode, purpose_impedance[mode], i)
                        mtx_pos = (i, 0, 0)
                        dtm.add_demand(purpose.name, mode, demand, mtx_pos)
            else:
                demand = purpose.calc_demand(purpose_impedance)
                self._validate_demand(demand)
                mtx_pos = (purpose.bounds[0], 0)
                if purpose.dest != "source":
                    for mode in demand:
                        dtm.add_demand(purpose.name, mode, demand[mode], mtx_pos)
        pos = ass_model.mapping[parameters.first_external_zone]
        for mode in parameters.external_modes:
            if mode == "truck":
                int_demand = trucks.sum(0) + trucks.sum(1)
            elif mode == "trailer_truck":
                int_demand = trailer_trucks.sum(0) + trailer_trucks.sum(1)
            else:
                int_demand = numpy.zeros(zdata_base.nr_zones)
                for purpose in dm.tour_purposes:
                    if purpose.dest != "source":
                        l, u = purpose.bounds
                        int_demand[l:u] += purpose.generated_tours[mode]
                        int_demand += purpose.attracted_tours[mode]
            ext_demand = em.calc_external(mode, int_demand)
            dtm.add_demand("external", mode, ext_demand, (pos, 0))
        impedance = {}
        for tp in parameters.emme_scenario:
            n = ass_model.mapping[parameters.first_external_zone]
            dtm.add_vans(tp, n)
            ass_model.assign(tp, dtm.demand[tp])
            impedance[tp] = ass_model.get_impedance()
        dtm.init_demand()
        self.assertEquals(len(parameters.emme_scenario), len(impedance))
        self._validate_impedances(impedance["aht"])
        self._validate_impedances(impedance["pt"])
        self._validate_impedances(impedance["iht"])
        
        print("Assignment test done")
    
    def _validate_impedances(self, impedances):
        self.assertIsNotNone(impedances)
        self.assertIs(type(impedances), dict)
        self.assertEquals(len(impedances), 3)
        self.assertIsNotNone(impedances["time"])
        self.assertIsNotNone(impedances["cost"])
        self.assertIsNotNone(impedances["dist"])
        self.assertIs(type(impedances["time"]), dict)
        self.assertEquals(len(impedances["time"]), 5)
        self.assertIsNotNone(impedances["time"]["transit"])
        self.assertIs(type(impedances["time"]["transit"]), numpy.ndarray)
        self.assertEquals(impedances["time"]["transit"].ndim, 2)
        self.assertEquals(len(impedances["time"]["transit"]), 8)

    def _validate_demand(self, demand):
        self.assertIsNotNone(demand)
        self.assertIs(type(demand), dict)
        self.assertIsNotNone(demand["transit"])
        self.assertIs(type(demand["transit"]), numpy.ndarray)
        self.assertEquals(demand["transit"].ndim, 2)
        self.assertEquals(demand["transit"].shape[1], 6)
        