#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import json
import numpy
import unittest
import openmatrix as omx

from datatypes.purpose import FreightPurpose
from datahandling.zonedata import BaseZoneData
from datahandling.zonedata import ZoneData
from datahandling.resultdata import ResultsData
from assignment.emme_bindings.emme_project import EmmeProject
from assignment.emme_assignment import EmmeAssignmentModel
from utils.freight_costs import calc_rail_cost, calc_road_cost, calc_ship_cost
from utils.read_csv_file import read_mapping


TEST_DATA_PATH = Path(__file__).parent.parent / "test_data"
PARAMETERS_PATH = Path(__file__).parent.parent.parent / "parameters" / "freight"
ZONE_NUMBERS = numpy.loadtxt(
    TEST_DATA_PATH / "Scenario_input_data" / "2030_test" / "freight_zones.csv")


class FreightModelTest(unittest.TestCase):

    def test_freight_model(self):      
        inputdata = TEST_DATA_PATH / "Scenario_input_data" / "2030_test"
        resultpath = TEST_DATA_PATH / "Results" / "test" / "freight"
        resultdata = ResultsData(resultpath)
        submodel = "koko_suomi_kunta"
        mapping = read_mapping(inputdata / f"{submodel}.zmp")
        basezonedata = BaseZoneData(inputdata, numpy.array(ZONE_NUMBERS), mapping)
        zonedata = ZoneData(inputdata, numpy.array(ZONE_NUMBERS),
                            basezonedata.aggregations, mapping)
        with open(inputdata / "comm_finage_conversion.json") as f:
            comm_conversion = json.load(f)
        purposes = {}
        for file_name in os.listdir(PARAMETERS_PATH):
            if file_name.endswith(".json"):
                with open(os.path.join(PARAMETERS_PATH, file_name), 'r') as file:
                    comm_params = json.load(file)
                    comm = file_name.split("_")[0]
                    purposes[comm] = FreightPurpose(comm_params, zonedata, resultdata)
        freight_costdata = self.read_freight_costdata(inputdata)
        ass_model = EmmeAssignmentModel(
            EmmeProject("C:\\emmeproj\\freight_kunta\\freight_kunta.emp"), first_scenario_id=11)
        ass_model.prepare_freight_network(zonedata.car_dist_cost, list(purposes))
        temp_impedance = ass_model.freight_network.assign()
        omx_file = omx.open_file(resultpath / "freight_demand_tons_year.omx", "w")
        omx_file.create_mapping("zone_number", ZONE_NUMBERS)
        for purpose_key, purpose_value in purposes.items():
            base_comm = comm_conversion[purpose_key]
            impedance = {
                "truck": {
                    "cost": calc_road_cost(freight_costdata["truck"][base_comm],
                                           temp_impedance["dist"]["truck"],
                                           temp_impedance["time"]["truck"])
                },
                "freight_train": {
                    "cost": calc_rail_cost(freight_costdata["freight_train"][base_comm],
                                           freight_costdata["truck"][base_comm],
                                           temp_impedance["dist"]["freight_train"],
                                           temp_impedance["time"]["freight_train"],
                                           temp_impedance["aux_dist"]["freight_train"],
                                           temp_impedance["aux_time"]["freight_train"])
                },
                "ship": {"cost": calc_ship_cost(freight_costdata["ship"][base_comm],
                                                freight_costdata["truck"][base_comm],
                                                temp_impedance["dist"]["ship"],
                                                temp_impedance["aux_dist"]["ship"],
                                                temp_impedance["aux_time"]["ship"])}
            }
            if base_comm in ("elint", "jate"):
                del impedance["ship"]
            demand = purpose_value.calc_traffic(impedance, purpose_key)
            if "ship" not in demand.keys():
                demand["ship"] = numpy.zeros(demand["truck"].shape, dtype=numpy.float32)
            for mode in demand:
                new_demand = numpy.nan_to_num(demand[mode])
                omx_file[f"{purpose_key}_{mode}"] = new_demand
                ass_model.freight_network.set_matrix(mode, new_demand)
            ass_model.freight_network.save_network_volumes(purpose_key)
            ass_model.freight_network.output_traversal_matrix(resultpath, purpose_key)
        omx_file.close()

    def read_freight_costdata(self, path: Path) -> dict:
        freight_costdata = {
            "truck": "freight_truck_costs.json",
            "freight_train": "freight_train_costs.json",
            "ship": "freight_ship_costs.json"
        }
        for k,v in freight_costdata.items():
            with open(path / v) as f:
                freight_costdata[k] = json.load(f)
        return freight_costdata
    
test = FreightModelTest()
test.test_freight_model()
