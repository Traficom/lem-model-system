#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import pandas
import numpy
import unittest

from datatypes.purpose import FreightPurpose
from datahandling.zonedata import ZoneData
from datahandling.resultdata import ResultsData
from assignment.emme_bindings.emme_project import EmmeProject
from assignment.emme_assignment import EmmeAssignmentModel
from assignment.departure_time import DirectDepartureTimeModel


TEST_DATA_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "..", "test_data")
METROPOLITAN_ZONES = numpy.loadtxt(
    os.path.join(TEST_DATA_PATH, "Scenario_input_data",
                 "2030_test", "freight_zones.csv"))
MODEL_TYPE = "dest_mode"
ESTIM_TYPE = "attr"

class FreightModelTest(unittest.TestCase):

    def test_freight_model(self):

        def get_cost_mtx(mtx_path: str, purpose_key) -> numpy.array:
            mtx = pandas.read_csv(
                os.path.join(TEST_DATA_PATH, "Scenario_input_data",
                             "2030_test", mtx_path))
            mtx = mtx.query(f"commodity_id == {purpose_key} \
                                & from_id in {METROPOLITAN_ZONES.tolist()} \
                                & to_id in {METROPOLITAN_ZONES.tolist()}")
            mtx = numpy.array(mtx["cost"])
            mtx.shape = (len(METROPOLITAN_ZONES), len(METROPOLITAN_ZONES))
            return mtx

        def mtx_to_df(commodity_id: str, mode_mtx: numpy.ndarray, mode_id: int):
            df = pandas.DataFrame(data=mode_mtx,
                                  index=METROPOLITAN_ZONES,
                                  columns=METROPOLITAN_ZONES)\
                                .reset_index()
            df = df.melt(id_vars="index",
                         value_vars=METROPOLITAN_ZONES)
            df = df.rename(columns={"index": "from_id",
                                    "variable": "to_id",
                                    "value": "demand"})
            df.loc[:, "commodity_id"] = commodity_id
            df.loc[:, "mode_id"] = mode_id
            df = df.astype({"from_id": "int32", "to_id": "int32",
                            "demand": "float64", "commodity_id": "int32",
                            "mode_id": "int32"})
            return df

        resultdata = ResultsData(os.path.join(TEST_DATA_PATH, "Results",
                                              "test", "freight", MODEL_TYPE))
        zonedata = ZoneData(
            os.path.join(TEST_DATA_PATH, "Scenario_input_data", "2030_test"),
            numpy.array(METROPOLITAN_ZONES),
            "freight_zones.zmp"
            )
        parameters_path = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), "..", "..", "parameters",
                "freight", MODEL_TYPE)
        purposes = {}
        for file_name in os.listdir(parameters_path):
            if file_name.endswith(".json"):
                with open(os.path.join(parameters_path, file_name), 'r') as file:
                    fname = file_name.split("_")[1]
                    purposes[fname] = FreightPurpose(json.load(file), zonedata,
                                                    resultdata)
        ass_model = EmmeAssignmentModel(
            EmmeProject("emme_project_path"), first_scenario_id=1)
        ass_model.prepare_freight_network(zonedata.car_dist_cost)
        temp_impedance = ass_model.freight_network.assign()
        dtm = DirectDepartureTimeModel(self.ass_model)
        demand_list = {}
        for purpose_key, purpose_value in purposes.items():
            impedance = {
                "truck": {
                    "cost": (a*temp_impedance["time"]["truck"]
                             + b*temp_impedance["dist"]["truck"]),
                },
                "train": {
                    "cost": (c*temp_impedance["dist"]["rail"]
                             + d*temp_impedance["aux_dist"]["rail"]
                             + e*temp_impedance["aux_time"]["rail"]),
                },
                "ship": {
                    "cost": (f*temp_impedance["dist"]["ship4"]
                             + g*temp_impedance["aux_dist"]["ship4"]
                             + h*temp_impedance["aux_time"]["ship4"]),
                },
            }
            demand = purpose_value.calc_traffic(impedance)
            for mode in demand:
                dtm.add_demand(demand[mode])
            demand_list[purpose_key] = demand
        ass_model.freight_network.assign()

        df_list = []
        for key, val in demand_list.items():
            df_truck = mtx_to_df(key, val["truck"], 1)
            df_train = mtx_to_df(key, val["train"], 2)
            df_ship = mtx_to_df(key, val["ship"], 3)
            df = pandas.concat([df_truck, df_train, df_ship], axis=0)
            df_list.append(df)
        # Concats all commodity ids
        df = pandas.concat(df_list, axis=0)
        df.to_pickle(os.path.join(
            TEST_DATA_PATH, "Results", "test", "freight",
            MODEL_TYPE, f"{MODEL_TYPE}_demand_{ESTIM_TYPE}_new_shiptons.pkl"),
            compression="infer")
