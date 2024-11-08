from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Union, cast
from collections import defaultdict
import numpy
import pandas
from math import log10

import utils.log as log
import parameters.assignment as param
from assignment.abstract_assignment import AssignmentModel
from assignment.assignment_period import AssignmentPeriod
from assignment.freight_assignment import FreightAssignmentPeriod
if TYPE_CHECKING:
    from assignment.emme_bindings.emme_project import EmmeProject
    from datahandling.resultdata import ResultsData
    from inro.emme.database.scenario import Scenario # type: ignore
    from inro.emme.network.Network import Network # type: ignore


class EmmeAssignmentModel(AssignmentModel):
    """
    Emme assignment definition.

    Parameters
    ----------
    emme_context : assignment.emme_bindings.emme_project.EmmeProject
        Emme projekt to connect to this assignment
    first_scenario_id : int
        Id fo EMME scenario where network is stored and modified.
    separate_emme_scenarios : bool (optional)
        Whether four new scenarios will be created in EMME
        (with ids following directly after first scenario id)
        for storing time-period specific network results:
        day, morning rush hour, midday hour and afternoon rush hour.
    save_matrices : bool (optional)
        Whether matrices will be saved in Emme format for all time periods.
        If false, Emme matrix ids 0-99 will be used for all time periods.
    use_free_flow_speeds : bool (optional)
        Whether traffic assignment is all-or-nothing with free-flow speeds.
    use_stored_speeds : bool (optional)
        Whether traffic assignment is all-or-nothing with speeds stored
        in `@car_time_xxx`. Overrides `use_free_flow_speeds` if this is
        also set to `True`.
    delete_extra_matrices : bool (optional)
        If True, only matrices needed for demand calculation will be
        returned from end assignment.
    time_periods : list of str (optional)
            Time period names, default is aht, pt, iht
    first_matrix_id : int (optional)
        Where to save matrices (if saved),
        300 matrix ids will be reserved, starting from first_matrix_id.
        Default is 100(-399).
    """
    def __init__(self, 
                 emme_context: EmmeProject,
                 first_scenario_id: int,
                 separate_emme_scenarios: bool = False,
                 save_matrices: bool = False,
                 use_free_flow_speeds: bool = False,
                 use_stored_speeds: bool = False,
                 delete_extra_matrices: bool = False,
                 time_periods: List[str] = param.time_periods, 
                 first_matrix_id: int = 100):
        self.separate_emme_scenarios = separate_emme_scenarios
        self.save_matrices = save_matrices
        self.use_free_flow_speeds = use_free_flow_speeds
        self.use_stored_speeds = use_stored_speeds
        self.delete_extra_matrices = delete_extra_matrices
        self.time_periods = time_periods
        self.first_matrix_id = first_matrix_id if save_matrices else 0
        self.emme_project = emme_context
        self.mod_scenario = self.emme_project.modeller.emmebank.scenario(
            first_scenario_id)
        if self.mod_scenario is None:
            raise ValueError(f"EMME project has no scenario {first_scenario_id}")

    def prepare_network(self, car_dist_unit_cost: Dict[str, float]):
        """Create matrices, extra attributes and calc background variables.

        Parameters
        ----------
        dist_unit_cost : dict
            key : str
                Assignment class (car_work/truck/...)
            value : float
                Car cost per km in euros
        """
        self._add_bus_stops()
        if self.separate_emme_scenarios:
            self.day_scenario = self.emme_project.copy_scenario(
                self.mod_scenario, self.mod_scenario.number + 1,
                self.mod_scenario.title + '_' + "vrk",
                overwrite=True, copy_paths=False, copy_strategies=False)
        else:
            self.day_scenario = self.mod_scenario
        matrix_types = tuple({mtx_type: None for ass_class
            in param.emme_matrices.values() for mtx_type in ass_class})
        ten = max(10, len(param.emme_matrices))
        id_ten = {result_type: i*ten for i, result_type
            in enumerate(matrix_types + param.transit_classes)}
        hundred = max(100, ten*len(matrix_types + param.transit_classes))
        self.assignment_periods = []
        for i, tp in enumerate(self.time_periods):
            if self.separate_emme_scenarios:
                scen_id = self.mod_scenario.number + i + 2
                self.emme_project.copy_scenario(
                    self.mod_scenario, scen_id,
                    self.mod_scenario.title + '_' + tp,
                    overwrite=True, copy_paths=False, copy_strategies=False)
            else:
                scen_id = self.mod_scenario.number
            emme_matrices = self._create_matrices(
                tp, i*hundred + self.first_matrix_id, id_ten)
            self.assignment_periods.append(AssignmentPeriod(
                tp, scen_id, self.emme_project, emme_matrices,
                separate_emme_scenarios=self.separate_emme_scenarios,
                use_free_flow_speeds=self.use_free_flow_speeds,
                use_stored_speeds=self.use_stored_speeds,
                delete_extra_matrices=self.delete_extra_matrices))
        ass_classes = list(param.emme_matrices) + ["bus"]
        ass_classes.remove("walk")
        self._create_attributes(
            self.day_scenario, ass_classes, self._extra, self._netfield,
            car_dist_unit_cost)
        self._segment_results = self._create_transit_attributes(
            self.day_scenario, self._extra)
        for ap in self.assignment_periods:
            ap.prepare(
                self._create_attributes(
                    ap.emme_scenario, ass_classes, ap.extra, ap.netfield,
                    car_dist_unit_cost),
                car_dist_unit_cost)
            ap.prepare_transit(
                *self._create_transit_attributes(ap.emme_scenario, ap.extra))
        self._init_functions()
        #add ferry wait time
        self.emme_project.set_extra_function_parameters(el1=param.ferry_wait_attr)

    def prepare_freight_network(self, car_dist_unit_cost: Dict[str, float],
                                commodity_classes: List[str]):
        """Create matrices, extra attributes and calc background variables.

        Parameters
        ----------
        dist_unit_cost : dict
            key : str
                Assignment class (car_work/truck/...)
            value : float
                Car cost per km in euros
        commodity_classes : list of str
            Class names for which we want extra attributes
        """
        mtxs = {}
        for i, ass_class in enumerate(param.freight_matrices, start=1):
            mtxs[ass_class] = {}
            for j, mtx_type in enumerate(param.freight_matrices[ass_class]):
                mtxs[ass_class][mtx_type] = f"mf{i*10 + j}"
                description = f"{mtx_type}_{ass_class}"
                self.emme_project.create_matrix(
                    matrix_id=mtxs[ass_class][mtx_type],
                    matrix_name=description, matrix_description=description,
                    overwrite=True)
        self.freight_network = FreightAssignmentPeriod(
            "vrk", self.mod_scenario.number, self.emme_project, mtxs,
            use_free_flow_speeds=True)
        self.assignment_periods = [self.freight_network]
        self.emme_project.create_extra_attribute(
            "TRANSIT_LINE", param.terminal_cost_attr, "terminal cost",
            overwrite=True, scenario=self.mod_scenario)
        for ass_class in param.freight_modes.values():
            for attr in ass_class.values():
                self.emme_project.create_extra_attribute(
                    "TRANSIT_LINE", attr, "terminal cost",
                    overwrite=True, scenario=self.mod_scenario)
        for comm_class in commodity_classes:
            for ass_class in param.freight_modes:
                attr_name = (comm_class + ass_class)[:17]
                self.emme_project.create_extra_attribute(
                    "TRANSIT_SEGMENT", '@' + attr_name,
                    "commodity flow", overwrite=True,
                    scenario=self.mod_scenario)
                self.emme_project.create_extra_attribute(
                    "LINK", '@a_' + attr_name,
                    "commodity flow", overwrite=True,
                    scenario=self.mod_scenario)
        self.freight_network.prepare(
            self._create_attributes(
                self.mod_scenario,
                list(param.truck_classes) + list(param.freight_modes),
                self._extra, self._netfield, car_dist_unit_cost),
            car_dist_unit_cost)
        self._init_functions()

    def _init_functions(self):
        for idx in param.volume_delay_funcs:
            try:
                self.emme_project.modeller.emmebank.delete_function(idx)
            except Exception:
                pass
            self.emme_project.modeller.emmebank.create_function(
                idx, param.volume_delay_funcs[idx])

    def init_assign(self):
        ap0 = self.assignment_periods[0]
        ap0.init_assign()
        if self.save_matrices:
            for ap in self.assignment_periods[1:]:
                self._copy_matrix("time", "bike", ap0, ap)
                self._copy_matrix("dist", "bike", ap0, ap)
                self._copy_matrix("time", "walk", ap0, ap)
                self._copy_matrix("dist", "walk", ap0, ap)

    @property
    def zone_numbers(self) -> List[int]:
        """List of all zone numbers. ???types"""
        return self.mod_scenario.zone_numbers

    @property
    def mapping(self) -> Dict[int, int]:
        """dict: Dictionary of zone numbers and corresponding indices."""
        mapping = {}
        for idx, zone in enumerate(self.zone_numbers):
            mapping[zone] = idx
        return mapping

    @property
    def nr_zones(self) -> int:
        """int: Number of zones in assignment model."""
        return len(self.zone_numbers)

    @property
    def beeline_dist(self):
        log.info("Get beeline distances from network centroids")
        network = self.mod_scenario.get_network()
        centroids = [numpy.array([0.001 * node.x, 0.001 * node.y])
                              for node in network.centroids()]
        centr_array = numpy.array(centroids)
        mtx = numpy.zeros(
            shape=(len(centroids), len(centroids)), dtype=numpy.float32)
        for i, centr in enumerate(centroids):
            mtx[i, :] = numpy.sqrt(numpy.sum((centr_array - centr) ** 2, axis=1))
        return mtx

    def aggregate_results(self,
                          resultdata: ResultsData,
                          mapping: pandas.Series):
        """Aggregate results to 24h and print vehicle kms.

        Parameters
        ----------
        resultdata : datahandling.resultdata.Resultdata
            Result data container to print to
        mapping : pandas.Series
            Mapping between municipality and county
        """
        car_times = pandas.DataFrame(
            {ap.netfield("car_time"): ap.get_car_times()
                for ap in self.assignment_periods})
        car_times.index.names = ("i_node", "j_node")
        resultdata.print_data(car_times, "netfield_links.txt")

        # Aggregate results to 24h
        for ap in self.assignment_periods:
            ap.transit_results_links_nodes()
        for transit_class in param.transit_classes:
            for res in param.segment_results:
                self._transit_segment_24h(
                    transit_class, param.segment_results[res])
                if res != "transit_volumes":
                    self._node_24h(
                        transit_class, param.segment_results[res])
        ass_classes = list(param.emme_matrices) + ["bus", "aux_transit"]
        ass_classes.remove("walk")
        for ass_class in ass_classes:
            self._link_24h(ass_class)

        # Aggregate and print vehicle kms and link lengths
        kms = dict.fromkeys(ass_classes, 0.0)
        vdfs = {param.roadclasses[linktype].volume_delay_func
            for linktype in param.roadclasses}
        vdfs.add(0) # Links with car traffic prohibited
        vdf_kms = pandas.concat(
            {ass_class: pandas.Series(0.0, vdfs, name="veh_km")
                for ass_class in ass_classes},
            names=["class", "v/d-func"])
        areas = mapping.drop_duplicates()
        area_kms = {ass_class: pandas.Series(0.0, areas)
            for ass_class in ass_classes}
        vdf_area_kms = {vdf: pandas.Series(0.0, areas) for vdf in vdfs}
        #The following line only works well in Python 3.7+
        linktypes = (list(dict.fromkeys(param.roadtypes.values()))
                     + list(dict.fromkeys(param.railtypes.values())))
        linklengths = pandas.Series(0.0, linktypes, name="length")
        soft_modes = param.transit_classes + ("bike",)
        network = self.day_scenario.get_network()
        faulty_kela_code_nodes = set()
        for link in network.links():
            linktype = link.type % 100
            if linktype in param.roadclasses:
                vdf = param.roadclasses[linktype].volume_delay_func
            elif linktype in param.custom_roadtypes:
                vdf = linktype - 90
            else:
                vdf = 0
            municipality = link.i_node["#municipality"]
            try:
                area = mapping[municipality]
            except KeyError:
                faulty_kela_code_nodes.add(municipality)
                area = None
            for ass_class in ass_classes:
                veh_kms = link[self._extra(ass_class)] * link.length
                kms[ass_class] += veh_kms
                if vdf in vdfs:
                    vdf_kms[ass_class][vdf] += veh_kms
                if area in areas:
                    area_kms[ass_class][area] += veh_kms
                if (vdf in vdfs
                        and area in vdf_area_kms[vdf]
                        and ass_class not in soft_modes):
                    vdf_area_kms[vdf][area] += veh_kms
            if vdf == 0 and linktype in param.railtypes:
                linklengths[param.railtypes[linktype]] += link.length
            else:
                linklengths[param.roadtypes[vdf]] += link.length / 2
        if faulty_kela_code_nodes:
            s = ("County not found for #municipality when aggregating link data: "
                 + ", ".join(faulty_kela_code_nodes))
            log.warn(s)
        resultdata.print_line("\nVehicle kilometres", "result_summary")
        resultdata.print_concat(vdf_kms, "vehicle_kms_vdfs.txt")
        for ass_class in ass_classes:
            resultdata.print_line(
                "{}:\t{:1.0f}".format(ass_class, kms[ass_class]),
                "result_summary")
        resultdata.print_data(area_kms, "vehicle_kms_county.txt")
        resultdata.print_data(vdf_area_kms, "vehicle_kms_vdfs_county.txt")
        resultdata.print_data(linklengths, "link_lengths.txt")

        # Print mode boardings per municipality
        boardings = defaultdict(lambda: defaultdict(float))
        attrs = [transit_class["total_boardings"]
            for transit_class in self._segment_results[0].values()]
        for line in network.transit_lines():
            mode = line.mode.id
            for seg in line.segments():
                for tc in attrs:
                    boardings[mode][seg.i_node["#municipality"]] += seg[tc]
        resultdata.print_data(
            pandas.DataFrame.from_dict(boardings), "municipality_boardings.txt")

        # Aggregate and print numbers of stations
        stations = pandas.Series(0, param.station_ids, name="number")
        for node in network.regular_nodes():
            for mode in param.station_ids:
                if (node.data2 == param.station_ids[mode]
                        and node[self._extra("transit_won_boa")] > 0):
                    stations[mode] += 1
                    break
        resultdata.print_data(stations, "transit_stations.txt")

        # Aggregate and print transit vehicle kms
        transit_modes = [veh.description for veh in network.transit_vehicles()]
        miles = {miletype: pandas.Series(0.0, transit_modes)
            for miletype in ("dist", "time")}
        for ap in self.assignment_periods:
            network = ap.emme_scenario.get_network()
            volume_factor = param.volume_factors["bus"][ap.name]
            time_attr = ap.extra(param.uncongested_transit_time)
            for line in network.transit_lines():
                mode = line.vehicle.description
                headway = line[ap.netfield("hdw")]
                if 0 < headway < 990:
                    departures = volume_factor * 60/headway
                    for segment in line.segments():
                        miles["dist"][mode] += departures * segment.link.length
                        miles["time"][mode] += departures * segment[time_attr]
        resultdata.print_data(miles, "transit_kms.txt")

    def calc_transit_cost(self, fares: pandas.DataFrame):
        """Insert line costs.
        
        Parameters
        ----------
        fares : pandas.DataFrame
            Transit fare zone specification
        """
        if self.separate_emme_scenarios:
            for ap in self.assignment_periods:
                ap.calc_transit_cost(fares)
        else:
            self.assignment_periods[0].calc_transit_cost(fares)

    def _copy_matrix(self, 
                     mtx_type: str, 
                     ass_class: str, 
                     ass_period_1: AssignmentPeriod, 
                     ass_period_2: AssignmentPeriod):
        from_mtx = ass_period_1.emme_matrices[ass_class][mtx_type]
        to_mtx = ass_period_2.emme_matrices[ass_class][mtx_type]
        description = f"{mtx_type}_{ass_class}_{ass_period_2.name}"
        scenario = self.mod_scenario
        self.emme_project.copy_matrix(
            from_mtx, to_mtx, description, description, scenario)

    def _extra(self, attr: str) -> str:
        """Add prefix "@" and suffix "_vrk".

        Parameters
        ----------
        attr : str
            Attribute string to modify

        Returns
        -------
        str
            Modified string
        """
        return "@{}_{}".format(attr, "vrk")

    def _netfield(self, attr: str) -> str:
        """Add prefix "#" and suffix "_vrk".

        Parameters
        ----------
        attr : str
            Attribute string to modify

        Returns
        -------
        str
            Modified string
        """
        return "#{}_{}".format(attr, "vrk")

    def _add_bus_stops(self):
        network: Network = self.mod_scenario.get_network()
        for line in network.transit_lines():
            if line.mode.id in param.stop_codes:
                if not line[param.keep_stops_attr]:
                    is_stop_field = param.stop_codes[line.mode.id]
                    for segment in line.segments():
                        is_stop = segment.i_node[is_stop_field]
                        segment.allow_alightings = is_stop
                        segment.allow_boardings = is_stop
            try:
                dwell_time = param.bus_dwell_time[line.mode.id]
            except KeyError:
                pass
            else:
                for segment in line.segments():
                    if segment.dwell_time < 2:
                        # Unless a longer stop is scheduled,
                        # we set default dwell time for buses
                        segment.dwell_time = (dwell_time
                            if segment.allow_boardings else 0)
        self.mod_scenario.publish_network(network)

    def _create_matrices(self, time_period, id_hundred, id_ten):
        """Create EMME matrices for storing demand and impedance.

        Parameters
        ----------
        time_period : str
            Time period name (aht, pt, iht)
        id_hundred : int
            A new hundred in the matrix id space marks new assignment period
        id_ten : dict
            key : str
                Matrix type (demand/time/cost/dist/...)
            value : int
                A new ten in the matrix id space marks new type of matrix

        Returns
        -------
        dict
            key : str
                Assignment class (car_work/transit_leisure/...)
            value : dict
                key : str
                    Matrix type (demand/time/cost/dist/...)
                value : str
                    EMME matrix id
        """
        tag = time_period if self.save_matrices else ""
        emme_matrices = {}
        for i, ass_class in enumerate(param.emme_matrices, start=1):
            matrix_ids = {}
            for mtx_type in param.emme_matrices[ass_class]:
                _id_hundred = (id_hundred
                    if self.save_matrices or mtx_type == "demand" else 0)
                matrix_ids[mtx_type] = "mf{}".format(
                    _id_hundred + id_ten[mtx_type] + i)
                description = f"{mtx_type}_{ass_class}_{tag}"
                self._create_matrix(
                    matrix_id=matrix_ids[mtx_type],
                    matrix_name=description, matrix_description=description,
                    overwrite=True)
            if ass_class in param.transit_classes:
                j = 0
                for subset, parts in param.transit_impedance_matrices.items():
                    matrix_ids[subset] = {}
                    for mtx_type, longer_name in parts.items():
                        j += 1
                        id = f"mf{_id_hundred + id_ten[ass_class] + j}"
                        matrix_ids[subset][longer_name] = id
                        matrix_ids[mtx_type] = id
                        self._create_matrix(
                            matrix_id=id,
                            matrix_name=f"{mtx_type}_{ass_class}_{tag}",
                            matrix_description=longer_name,
                            default_value=999999, overwrite=True)
            emme_matrices[ass_class] = matrix_ids
        return emme_matrices

    def _create_matrix(self,
                       matrix_id: str,
                       matrix_name: str,
                       matrix_description: str,
                       default_value: float = 0.0,
                       overwrite: bool = False):
        """Create matrix in EMME.

        Due to an issue in Modeller, `create_matrix` with `overwrite=True`
        does not scale well for many large matrices. This is a workaround.
        """
        if overwrite:
            emmebank = self.emme_project.modeller.emmebank
            if emmebank.matrix(matrix_id) is not None:
                emmebank.delete_matrix(matrix_id)
        self.emme_project.create_matrix(
            matrix_id, matrix_name, matrix_description, default_value)

    def _create_attributes(self,
                           scenario: Any,
                           assignment_classes: List[str],
                           extra: Callable[[str], str],
                           netfield: Callable[[str], str],
                           link_costs: Dict[str, float]
            ) -> Dict[str, Union[str, float]]:
        """Create extra attributes needed in assignment.

        Parameters
        ----------
        scenario : inro.modeller.emmebank.scenario
            Emme scenario to create attributes for
        assignment_classes : list of str
            Names of assignment classes to create volume attributes for
        extra : function
            Small helper function which modifies string
            (e.g., self._extra)
        netfield : function
            Small helper function which modifies string
            (e.g., self._netfield)
        link_costs : dict
            key : str
                Assignment class (car_work/truck/...)
            value : float
                Car cost per km in euros

        Returns
        -------
        dict
            key : str
                Assignment class (car_work/truck/...)
            value : str or float
                Extra attribute where link cost is found (str) or length
                multiplier to calculate link cost (float)
        """
        if TYPE_CHECKING: scenario = cast(Scenario, scenario)
        for ass_class in assignment_classes:
            self.emme_project.create_extra_attribute(
                "LINK", extra(ass_class), ass_class + " volume",
                overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "LINK", param.aux_car_time_attr, "walk time",
            overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "LINK", extra("truck_time"), "truck time",
            overwrite=True, scenario=scenario)
        if scenario.network_field("LINK", netfield("hinta")) is not None:
            self.emme_project.create_extra_attribute(
                "LINK", extra("toll_cost"), "toll cost",
                overwrite=True, scenario=scenario)
            link_costs: Dict[str, str] = {}
            for ass_class in param.assignment_modes:
                attr_name = extra(f"cost_{ass_class[:10]}")
                link_costs[ass_class] = attr_name
                self.emme_project.create_extra_attribute(
                    "LINK", attr_name, "total cost",
                    overwrite=True, scenario=scenario)
        log.debug("Created extra attributes for scenario {}".format(
            scenario))
        return link_costs

    def _create_transit_attributes(self,
                                   scenario: Any,
                                   extra: Callable[[str], str],
            ) -> Tuple[Dict[str,Dict[str,str]], Dict[str, str]]:
        """Create extra attributes needed in assignment.

        Parameters
        ----------
        scenario : inro.modeller.emmebank.scenario
            Emme scenario to create attributes for
        extra : function
            Small helper function which modifies string
            (e.g., self._extra)

        Returns
        -------
        dict
            key : str
                Transit class (transit_work/transit_leisure/...)
            value : dict
                key : str
                    Segment result (transit_volumes/...)
                value : str
                    Extra attribute name (@transit_work_vol_aht/...)
        dict
            key : str
                Transit class (transit_work/transit_leisure/...)
            value : str or False
                Extra attribute name for park-and-ride aux volume if
                this is park-and-ride assignment, else False
        """
        # Create link attributes
        self.emme_project.create_extra_attribute(
            "LINK", extra("aux_transit"), "aux transit volume",
            overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "LINK", param.park_cost_attr_l, "terminal parking cost",
            overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "LINK", param.aux_transit_time_attr, "walk time",
            overwrite=True, scenario=scenario)
        # Create transit line attributes
        self.emme_project.create_extra_attribute(
            "TRANSIT_SEGMENT", param.dist_fare_attr,
            "distance fare attribute", overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "TRANSIT_LINE", param.board_fare_attr,
            "boarding fare attribute", overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "TRANSIT_LINE", param.board_long_dist_attr,
            "boarding fare attribute", overwrite=True, scenario=scenario)
        for transit_class in param.transfer_penalty:
            self.emme_project.create_extra_attribute(
                "TRANSIT_LINE", param.boarding_penalty_attr + transit_class,
                "boarding pentalty attribute", overwrite=True,
                scenario=scenario)
        # Create node and transit segment attributes
        attr = param.segment_results
        segment_results = {}
        park_and_ride_results = {}
        for tc in param.transit_classes:
            segment_results[tc] = {}
            for res in param.segment_results:
                attr_name = extra(tc[:11] + "_" + attr[res])
                segment_results[tc][res] = attr_name
                self.emme_project.create_extra_attribute(
                    "TRANSIT_SEGMENT", attr_name,
                    tc + " " + res, overwrite=True, scenario=scenario)
                if res != "transit_volumes":
                    self.emme_project.create_extra_attribute(
                        "NODE", extra(tc[:10] + "n_" + attr[res]),
                        tc + " " + res, overwrite=True, scenario=scenario)
            if tc in param.mixed_mode_classes:
                attr_name = extra(tc[0] + tc[2:] + "_aux")
                park_and_ride_results[tc] = attr_name
                self.emme_project.create_extra_attribute(
                    "LINK", attr_name, tc,
                    overwrite=True, scenario=scenario)
            else:
                park_and_ride_results[tc] = False
        self.emme_project.create_extra_attribute(
            "TRANSIT_SEGMENT", param.extra_waiting_time["penalty"],
            "wait time st.dev.", overwrite=True, scenario=scenario)
        self.emme_project.create_extra_attribute(
            "TRANSIT_SEGMENT", extra(param.uncongested_transit_time),
            "uncongested transit time", overwrite=True, scenario=scenario)
        log.debug("Created extra attributes for scenario {}".format(
            scenario))
        return segment_results, park_and_ride_results

    def calc_noise(self, mapping: pandas.Series) -> pandas.Series:
        """Calculate noise according to Road Traffic Noise Nordic 1996.

        Parameters
        ----------
        mapping : pandas.Series
            Mapping between municipality and county

        Returns
        -------
        pandas.Series
            Area (km2) of noise polluted zone, aggregated to area level
        """
        noise_areas = pandas.Series(
            0.0, mapping.drop_duplicates(), name="county")
        network = self.day_scenario.get_network()
        morning_network = self.assignment_periods[0].emme_scenario.get_network()
        for link in network.links():
            # Aggregate traffic
            light_modes = (
                self._extra("car_work"),
                self._extra("car_leisure"),
                self._extra("van"),
            )
            traffic = sum([link[mode] for mode in light_modes])
            rlink = link.reverse_link
            if rlink is None:
                reverse_traffic = 0
            else:
                reverse_traffic = sum([rlink[mode] for mode in light_modes])
            cross_traffic = (param.years_average_day_factor
                             * param.share_7_22_of_day
                             * (traffic+reverse_traffic))
            heavy = (link[self._extra("truck")]
                     + link[self._extra("trailer_truck")])
            traffic = max(traffic, 0.01)
            heavy_share = heavy / (traffic+heavy)

            # Calculate speed
            link = morning_network.link(link.i_node, link.j_node)
            car_time_attr = self.assignment_periods[0].netfield("car_time")
            rlink = link.reverse_link
            if reverse_traffic > 0:
                speed = (60 * 2 * link.length
                         / (link[car_time_attr]+rlink[car_time_attr]))
            else:
                speed = (0.3*(60*link.length/link[car_time_attr])
                         + 0.7*link.data2)
            speed = max(speed, 50.0)

            # Calculate start noise
            if speed <= 90:
                heavy_correction = (10*log10((1-heavy_share)
                                    + 500*heavy_share/speed))
            else:
                heavy_correction = (10*log10((1-heavy_share)
                                    + 5.6*heavy_share*(90/speed)**3))
            start_noise = ((68 + 30*log10(speed/50)
                           + 10*log10(cross_traffic/15/1000)
                           + heavy_correction)
                if cross_traffic > 0 else 0)

            # Calculate noise zone width
            func = param.noise_zone_width
            for interval in func:
                if interval[0] <= start_noise < interval[1]:
                    zone_width = func[interval](start_noise - interval[0])
                    break

            # Calculate noise zone area and aggregate to area level
            try:
                area = mapping[link.i_node["#municipality"]]
            except KeyError:
                area = None
            if area in noise_areas:
                noise_areas[area] += 0.001 * zone_width * link.length
        return noise_areas

    def _link_24h(self, attr: str):
        """ 
        Sums and expands link volumes to 24h.

        Parameters
        ----------
        attr : str
            Attribute name that is usually key in param.emme_demand_mtx
        """
        networks = {ap.name: ap.emme_scenario.get_network()
            for ap in self.assignment_periods}
        extras = {ap.name: ap.extra(attr) for ap in self.assignment_periods}
        network = self.day_scenario.get_network()
        extra = self._extra(attr)
        # save link volumes to result network
        for link in network.links():
            day_attr = 0
            for tp in networks:
                try:
                    tp_link = networks[tp].link(link.i_node, link.j_node)
                    day_attr += (tp_link[extras[tp]]
                                 * param.volume_factors[attr][tp])
                except (AttributeError, TypeError):
                    pass
            link[extra] = day_attr
        self.day_scenario.publish_network(network)
        log.info("Link attribute {} aggregated to 24h (scenario {})".format(
            extra, self.day_scenario.id))

    def _node_24h(self, transit_class: str, attr: str):
        """ 
        Sums and expands node attributes to 24h.

        Parameters
        ----------
        transit_class : str
            Transit class (transit_work/transit_leisure)
        attr : str
            Attribute name that is usually in param.segment_results
        """
        attr = transit_class[:10] + 'n_' + attr
        networks = {ap.name: ap.emme_scenario.get_network()
            for ap in self.assignment_periods}
        extras = {ap.name: ap.extra(attr) for ap in self.assignment_periods}
        network = self.day_scenario.get_network()
        extra = self._extra(attr)
        # save node volumes to result network
        for node in network.nodes():
            day_attr = 0
            for tp in networks:
                try:
                    tp_node = networks[tp].node(node.id)
                    day_attr += (tp_node[extras[tp]]
                                 * param.volume_factors[transit_class][tp])
                except (AttributeError, TypeError):
                    pass
            node[extra] = day_attr
        self.day_scenario.publish_network(network)
        log.info("Node attribute {} aggregated to 24h (scenario {})".format(
            extra, self.day_scenario.id))

    def _transit_segment_24h(self, transit_class: str, attr: str):
        """ 
        Sums and expands transit attributes to 24h.

        Parameters
        ----------
        transit_class : str
            Transit class (transit_work/transit_leisure)
        attr : str
            Attribute name that is usually in param.segment_results
        """
        attr = transit_class[:11] + '_' + attr
        networks = {ap.name: ap.emme_scenario.get_network()
            for ap in self.assignment_periods}
        extras = {ap.name: ap.extra(attr) for ap in self.assignment_periods}
        network = self.day_scenario.get_network()
        extra = self._extra(attr)
        # save segment volumes to result network
        for segment in network.transit_segments():
            day_attr = 0
            for tp in networks:
                try:
                    tp_segment = networks[tp].transit_line(
                        segment.line.id).segment(segment.number)
                    day_attr += (tp_segment[extras[tp]]
                                 * param.volume_factors[transit_class][tp])
                except (AttributeError, TypeError):
                    pass
            segment[extra] = day_attr
        self.day_scenario.publish_network(network)
        log.info("Transit attribute {} aggregated to 24h (scenario {})".format(
            extra, self.day_scenario.id))
