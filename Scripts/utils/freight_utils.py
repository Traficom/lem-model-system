import json
import numpy
from pathlib import Path
from typing import Dict

import parameters.assignment as param
import utils.log as log
from datatypes.purpose import FreightPurpose
from datahandling.zonedata import FreightZoneData
from datahandling.resultdata import ResultsData
from datahandling.matrixdata import MatrixData
from assignment.freight_assignment import FreightAssignmentPeriod

from parameters.zone import finland_border_points, cluster_border_points
from parameters.commodity import commodity_conversion

def create_purposes(parameters_path: Path, zonedata: FreightZoneData, 
                    resultdata: ResultsData, costdata: Dict[str, dict]) -> dict:
    """Creates instances of FreightPurpose class for each model parameter json file
    in parameters path.

    Parameters
    ----------
    parameters_path : Path
        Path object to estimation model type folder containing model parameter
        json files
    zonedata : FreightZoneData
        freight zonedata container
    resultdata : ResultsData
        handler for result saving operations 
    costdata : Dict[str, dict]
        Freight purpose : Freight mode
            Freight mode (truck/freight_train/ship) : mode
                Mode (truck/trailer_truck...) : unit cost name
                    unit cost name : unit cost value

    Returns
    -------
    dict[str, FreightPurpose]
        purpose name : FreightPurpose
    """
    purposes = {}
    for file in parameters_path.rglob("*.json"):
        commodity_params = json.loads(file.read_text("utf-8"))
        commodity = commodity_params["name"]
        try:
            purpose_cost = costdata[commodity_conversion[commodity]]
            purposes[commodity] = FreightPurpose(commodity_params, zonedata, 
                                                 resultdata, purpose_cost)
        except KeyError:
            log.warn(f"Aggregated commodity class '{commodity_conversion[commodity]}' "
                      f"for commodity {commodity} not found in costs json.")
    return purposes

class StoreDemand():
    """Handles demand dimension compatibility when storing demand matrices 
    into Emme and omx-files.
    """

    def __init__(self, 
                 freight_network: FreightAssignmentPeriod, 
                 resultmatrices: MatrixData, 
                 all_zone_numbers: numpy.ndarray, 
                 zone_numbers: numpy.ndarray):
        self.network = freight_network
        self.resultmatrices = resultmatrices
        self.all_zones = all_zone_numbers
        self.zones = zone_numbers

    def store(self, mode: str, demand: numpy.ndarray, 
              omx_filename: str = "", key_prefix: str = ""):
        """Stores demand matrices into Emme and as omx if user has given
        name for the .omx file. 

        Parameters
        ----------
        mode : str
            freight mode/assignment class
        demand : numpy.ndarray
            matrix that is set to Emme
        omx_filename : str, by default empty string
            optional name of an external .omx file for saving results
        key_prefix : str, by default empty string
            optional name prefix for matrix e.g. purpose name
        """
        emme_mtx = self.assess_dimensions(demand)
        self.network.set_matrix(mode, emme_mtx)
        if omx_filename:
            with self.resultmatrices.open(omx_filename, self.network.name, 
                                          self.all_zones, m="a") as mtx:
                keyname = f"{key_prefix}_{mode}" if key_prefix else mode
                mtx[keyname] = emme_mtx

    def assess_dimensions(self, demand: numpy.ndarray) -> numpy.ndarray:
        """Evaluates whether given demand matrix needs to be padded with zones 
        to maintain zone compatibility with scenario's Emme network.

        Parameters
        ----------
        demand : numpy.ndarray
            type demand matrix which is assessed before setting into Emme

        Returns
        -------
        numpy.ndarray
            demand with/without zone padding
        """
        fill_mtx = demand
        nr_all_zones = self.all_zones.size
        nr_zones = self.zones.size
        if demand.size != nr_all_zones**2:
            fill_mtx = numpy.zeros([nr_all_zones, nr_all_zones], dtype=numpy.float32)
            fill_mtx[:nr_zones, :nr_zones] = demand
        return fill_mtx

class ReadShipImpedances():
    """Fetches freight foreign ship attribute information from transit lines
    and creates ship specific impedance matrices.
    """
    def __init__(self, all_zones: numpy.ndarray, trade_type: str):
        self.all_zones = all_zones
        self.trade_type = trade_type
        self.dist_attr = "dist"
        self.freq_attr = "frequency"
        match trade_type:
            case "export":
                self.origin = finland_border_points
                self.destination = cluster_border_points
            case "import":
                self.origin = cluster_border_points
                self.destination = finland_border_points

    def form_matrices(self, freight_network: FreightAssignmentPeriod) -> dict:
        """Creates impedance matrices for freight ships using transit line
        attribute data.

        Parameters
        ----------
        freight_network : FreightAssignmentPeriod
            Assignment period's access handle to scenario network
        
        Returns
        -------
        dict
            Mode (container_ship/general_cargo...) : attribute
                Type (dist/frequency) : numpy.ndarray
        """
        transit_lines = list(freight_network.emme_scenario.get_network().transit_lines())
        ext_zones = {
            "origin": self.filter_border_points(self.origin),
            "destination": self.filter_border_points(self.destination)
        }
        ship_impedances = {}
        for ship in param.freight_marine_modes:
            ship_impedances[ship] = {}
            ship_mode = next(iter(param.freight_marine_modes[ship]))
            for attr in (self.dist_attr, self.freq_attr):
                line_attributes = self.fetch_line_data(transit_lines, ship_mode, attr)
                ship_impedances[ship][attr] = self.to_matrix(line_attributes, ext_zones)
        return ship_impedances, ext_zones

    def filter_border_points(self, border_data: dict) -> numpy.ndarray:
        """Filters out border point centroids that don't exist in scenario's network. 
        
        Parameters
        ----------
        border_data : dict
            Border id (FIHEL/SESTO...) : attribute type
                Type (name/id) : attribute value, str | int
        
        Results
        -------
        numpy.ndarray
            centroids that exist in scenario's network
        """
        emme_ids = sorted([i["id"] for i in border_data.values()])
        intersect = numpy.intersect1d(self.all_zones, numpy.array(emme_ids))
        network_port_ids = {port_id: border_data[port_id]["id"] for port_id 
                            in border_data if border_data[port_id]["id"] in intersect}
        return network_port_ids

    def fetch_line_data(self, transit_lines: list, ship_mode: str, 
                        attribute: str) -> dict:
        """Fetches transit line attribute information. Fetching is performed 
        only for those transit lines that match object's trade type.
        
        Parameters
        ----------
        transit_lines : list
            transit line objects in scenario's network
        ship_mode : str
            mode of freight ship
        attribute : str
            name of attribute type

        Returns
        -------
        dict
            Line id (str) : line ut data (float)
        """
        line_attributes = {}
        for line in transit_lines:
            line_mode = str(line.mode)
            line_id = str(line.id)
            country_code = line_id[0:2]
            if line_mode == ship_mode:
                if country_code == "FI" and self.trade_type == "export":
                    line_attributes[line_id] = self.get_attribute(line, attribute)
                elif country_code != "FI" and self.trade_type == "import":
                    line_attributes[line_id] = self.get_attribute(line, attribute)
        return line_attributes

    def get_attribute(self, line, attribute: str) -> float:
        """Sets transit line ut attribute data with matching attribute name.
        
        Parameters
        ----------
        line : Emme TransitLine object
            transit line from which data is fetched
        attribute : str
            name that is matched with transit line ut data
        
        Returns
        -------
        float
            line ut data
        """
        match attribute:
            case self.dist_attr:
                return line.data1
            case self.freq_attr:
                return line.data2

    def to_matrix(self, line_attributes: dict, ext_zones: dict) -> dict:
        """Creates inf matrix and inserts attribute values into origin and 
        destination indeces of the matrix. OD pairs without trade route will
        retain their inf attribute value.
        
        Parameters
        ----------
        line_attributes : dict
            line id : line ut data
        ext_zones : dict
            External zone type (origin/destination) : border name id
                Name id (FIHEL/EETLL...) : emme centroid id
        
        Results
        -------
        numpy.ndarray
            Impedance matrix with index inserted transit line attribute data
        """
        ext_origin = list(ext_zones["origin"].values())
        ext_dest = list(ext_zones["destination"].values())
        impedance_matrix = numpy.ones((len(ext_origin), len(ext_dest))) * numpy.inf
        for line in line_attributes:
            line_OD = line.split("_")[0].split("-")
            O_index = ext_origin.index(self.origin[line_OD[0]]["id"])
            D_index = ext_dest.index(self.destination[line_OD[1]]["id"])
            impedance_matrix[O_index][D_index] = line_attributes[line]
        return impedance_matrix
