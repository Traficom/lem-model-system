from argparse import ArgumentTypeError
import unittest
import pandas
from pathlib import Path
from assignment.emme_bindings.mock_project import MockProject, MODE_TYPES
from assignment.datatypes.transit_fare import TransitFareZoneSpecification
from assignment.mock_assignment import MockAssignmentModel
from datahandling.matrixdata import MatrixData
from utils.validate_network import validate
from utils.validate_loaded_network import validate_loaded
from parameters.assignment import time_periods
import parameters.zone as zone_param
import copy

class EmmeAssignmentTest(unittest.TestCase):
    def test_assignment(self):
        context = MockProject()
        scenario_dir = Path(__file__).parent.parent / "test_data" / "Network"
        scenario_id = 19
        context.import_scenario(scenario_dir, scenario_id, "test")
        fares = TransitFareZoneSpecification(pandas.DataFrame({
            "fare": {
                "A": 59,
                "AB": 109,
                "dist": 3.0,
                "start": 35,
            },
        }))

        # mock_result_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
        #     "..", "test_data", "Results","test")
        #ass_model = MockAssignmentModel(MatrixData(mock_result_path))
        network0 = context.modeller.emmebank.scenario(scenario_id).get_network()
        #ass_model.prepare_network(network = network0) #the number is the car cost per km

        #Mode check
        network1 = copy.deepcopy(network0)
        network1.create_mode(MODE_TYPES["3"],"h")
        self.assertRaises(ValueError, validate,
            network1,
            fares)
        
        #Link check cases
        cases = [
                #Link check, link modes must not be empty
                {"node1_centroid":False,
                  "node2_centroid":False,
                  "link_modes":"",
                  "link_type":142,
                  "link_length":1.0},
                #Link check, link modes must not be just h
                {"node1_centroid":False,
                  "node2_centroid":False,
                  "link_modes":"h",
                  "link_type":142,
                  "link_length":1.0},
                #Link check, if link type is not 70 (vaihtokävely), then length must not be zero
                {"node1_centroid":False,
                  "node2_centroid":False,
                  "link_modes":"haf",
                  "link_type":142,
                  "link_length":0},
                #Link check, link should not have type 100
                {"node1_centroid":False,
                  "node2_centroid":False,
                  "link_modes":"haf",
                  "link_type":100,
                  "link_length":1.0},
                #Link check, link should not have type 999
                {"node1_centroid":False,
                  "node2_centroid":False,
                  "link_modes":"haf",
                  "link_type":999,
                  "link_length":1.0},
                  ]
        node1_id = 800900
        node2_id = 800901
        for case in cases:
            self.link_check_network(network0, fares, 
                    node1_id, case["node1_centroid"], 
                    node2_id, case["node2_centroid"], 
                    case["link_modes"],
                    case["link_type"],
                    case["link_length"])
    
        # #Link check, link must have VDF if car link
        # network = copy.deepcopy(network0)
        # node1 = network.create_node(node1_id, False)
        # node2 = network.create_node(node2_id, False)
        # link = network.create_link(node1_id, node2_id, "hc")
        # #Check if link type equals 1
        # link.type = 142
        # link.length = 1.0
        # link.volume_delay_func = 0
        # self.assertRaises(ValueError, validate,
        #     network,
        #     fares)   
        
        #Segment check, train or metro travel time us1=0 before stopping (noalin=0 or noboan=0)
        # Check line encoding, if row's @ccost=1
        # only if mode is type mr
        network = copy.deepcopy(network0)
        itinerary = []
        node1_id = "802118"
        node2_id = "802119"
        node3_id = "802120"
        itinerary.append(node1_id)
        itinerary.append(node2_id)
        itinerary.append(node3_id)
        node1 = network.create_node(node1_id, False)
        node2 = network.create_node(node2_id, False)
        node3 = network.create_node(node3_id, False)
        link = network.create_link(node1_id, node2_id, "mr")
        link = network.create_link(node2_id, node3_id, "mr")
        line = network.create_transit_line(
                            '3002A3', 5, itinerary)
        hdw_attrs = [f"#hdw_{tp}" for tp in time_periods]
        for hdwy in hdw_attrs:
            line[hdwy] = 5.0
        line._segments[0].data1 = 0
        line._segments[1].data1 = 0
        line._segments[0].allow_boardings = 0
        line._segments[0].allow_alightings = 0
        line._segments[1].allow_boardings = 1
        line._segments[1].allow_alightings = 1
        self.assertRaises(ValueError, validate_loaded,
            network,
            fares) 
        
        #Segment check, train or metro travel time us1 is not 0 before stopping (noalin=1 and noboan=1)
        # Check line encoding, if row's @ccost=1
        # only if mode is type mr
        network = copy.deepcopy(network0)
        itinerary = []
        node1_id = "802121"
        node2_id = "802122"
        node3_id = "802123"
        itinerary.append(node1_id)
        itinerary.append(node2_id)
        itinerary.append(node3_id)
        node1 = network.create_node(node1_id, False)
        node2 = network.create_node(node2_id, False)
        node3 = network.create_node(node3_id, False)
        link = network.create_link(node1_id, node2_id, "mr")
        link = network.create_link(node2_id, node3_id, "mr")
        line = network.create_transit_line(
                            '3002A4', 5, itinerary)
        hdw_attrs = [f"#hdw_{tp}" for tp in time_periods]
        for hdwy in hdw_attrs:
            line[hdwy] = 5.0
        line._segments[0].data1 = 5
        line._segments[1].data1 = 0
        line._segments[0].allow_boardings = 0
        line._segments[0].allow_alightings = 0
        line._segments[1].allow_boardings = 0
        line._segments[1].allow_alightings = 0
        self.assertRaises(ValueError, validate_loaded,
            network,
            fares) 

        #Line check, headway should not be 0,1
        network = copy.deepcopy(network0)
        itinerary = []
        itinerary.append("802113")
        itinerary.append("802114")
        line = network.create_transit_line(
                            '3002A2', 5, itinerary)
        hdw_attrs = [f"#hdw_{tp}" for tp in time_periods]
        for hdwy in hdw_attrs:
            line[hdwy] = 0.001
        self.assertRaises(ValueError, validate, network)

    def link_check_network(self, network0, fares, node1_id, 
                           node1_iscentroid, node2_id, node2_iscentroid, 
                           link_modes, link_type, link_length):

        network = copy.deepcopy(network0)
        node1 = network.create_node(node1_id, node1_iscentroid)
        node2 = network.create_node(node2_id, node2_iscentroid)
        link = network.create_link(node1_id, node2_id, link_modes)
        #Check if link type equals 1
        link.type = link_type
        link.length = link_length
        self.assertRaises(ValueError, validate,
            network,
            fares)

if __name__ == "__main__":
    EmmeAssignmentTest().test_assignment()
