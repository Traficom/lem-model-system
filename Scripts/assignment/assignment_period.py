from __future__ import annotations
import numpy # type: ignore
import pandas # type: ignore
import copy

from typing import TYPE_CHECKING, Any, Dict, Optional, Union
import utils.log as log
import parameters.assignment as param
import parameters.zone as zone_param
from assignment.datatypes.car_specification import CarSpecification
from assignment.datatypes.transit import TransitSpecification
from assignment.datatypes.journey_level import BOARDED_LOCAL, BOARDED_LONG_D
from assignment.datatypes.path_analysis import PathAnalysis
from assignment.abstract_assignment import Period
if TYPE_CHECKING:
    from assignment.emme_bindings.emme_project import EmmeProject
    from emme_context.modeller.emmebank import Scenario # type: ignore


class AssignmentPeriod(Period):
    """
    EMME assignment period definition.

    This typically represents an hour of the day, which may or may not
    have a dedicated EMME scenario. In case it does not have its own
    EMME scenario, assignment results are stored only in extra attributes.

    Parameters
    ----------
    name : str
        Time period name (aht/pt/iht)
    emme_scenario : int
        EMME scenario linked to the time period
    emme_context : assignment.emme_bindings.emme_project.EmmeProject
        Emme project to connect to this assignment
    emme_matrices : dict
        key : str
                Assignment class (car_work/transit_leisure/...)
            value : dict
                key : str
                    Matrix type (demand/time/c
                    
                    t/dist/...)
                value : str
                    EMME matrix id
    separate_emme_scenarios : bool (optional)
        Whether separate scenarios have been created in EMME
        for storing time-period specific network results.
    use_free_flow_speeds : bool (optional)
        Whether traffic assignment is all-or-nothing with free-flow speeds.
    use_stored_speeds : bool (optional)
        Whether traffic assignment is all-or-nothing with speeds stored
        in `@car_time_xxx`. Overrides `use_free_flow_speeds` if this is
        also set to `True`.
    """
    def __init__(self, name: str, emme_scenario: int,
                 emme_context: EmmeProject,
                 emme_matrices: Dict[str, Dict[str, Any]],
                 separate_emme_scenarios: bool = False,
                 use_free_flow_speeds: bool = False,
                 use_stored_speeds: bool = False):
        self.name = name
        self.emme_scenario: Scenario = emme_context.modeller.emmebank.scenario(
            emme_scenario)
        self.emme_project = emme_context
        self._separate_emme_scenarios = separate_emme_scenarios
        self.emme_matrices = emme_matrices
        self.dist_unit_cost = param.dist_unit_cost
        self.use_stored_speeds = use_stored_speeds
        self.stopping_criteria = copy.deepcopy(
            param.stopping_criteria)
        if use_free_flow_speeds or use_stored_speeds:
            for criteria in self.stopping_criteria.values():
                criteria["max_iterations"] = 0

    def extra(self, attr: str) -> str:
        """Add prefix "@" and time-period suffix.

        Parameters
        ----------
        attr : str
            Attribute string to modify

        Returns
        -------
        str
            Modified string
        """
        return "@{}_{}".format(attr, self.name)

    def prepare(self, segment_results: Dict[str, Dict[str, str]],
                park_and_ride_results: Dict[str, Union[str, bool]]):
        """Prepare network for assignment.

        Calculate road toll cost, set boarding penalties,
        and add buses to background traffic.

        Parameters
        ----------
        segment_results : dict
            key : str
                Transit class (transit_work/transit_leisure)
            value : dict
                key : str
                    Segment result (transit_volumes/...)
                value : str
                    Extra attribute name (@transit_work_vol_aht/...)
        park_and_ride_results : dict
            key : str
                Transit class (transit_work/transit_leisure/...)
            value : str or False
                Extra attribute name for park-and-ride aux volume if
                this is park-and-ride assignment, else False
        """
        self._segment_results = segment_results
        self._park_and_ride_results = park_and_ride_results
        self._calc_road_cost()
        self._calc_boarding_penalties()
        self._calc_background_traffic()
        self._specify()

    def assign(self, matrices: dict, iteration: Union[int,str]) -> Dict:
        """Assign cars, bikes and transit for one time period.

        Get travel impedance matrices for one time period from assignment.

        Parameters
        ----------
        matrices : dict
            Assignment class (car_work/transit/...) : numpy 2-d matrix
        iteration : int or str
            Iteration number (0, 1, 2, ...) or "init" or "last"

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (car_work/transit/...) : numpy 2-d matrix
        """
        self._set_emmebank_matrices(matrices, iteration=="last")
        if iteration=="init":
            self._assign_pedestrians()
            self._set_bike_vdfs()
            self._assign_bikes(self.emme_matrices["bike"]["dist"], "all")
        elif iteration==0:
            self._set_car_and_transit_vdfs()
            if not self._separate_emme_scenarios:
                self._calc_background_traffic()
            self._assign_cars(self.stopping_criteria["coarse"])
            self._calc_extra_wait_time()
            self._assign_transit()
        elif iteration==1:
            if not self._separate_emme_scenarios:
                self._set_car_and_transit_vdfs()
                self._calc_background_traffic()
            self._assign_cars(self.stopping_criteria["coarse"])
            self._calc_extra_wait_time()
            self._assign_transit()
            self._calc_background_traffic(include_trucks=True)
        elif isinstance(iteration, int) and iteration>1:
            if not self._separate_emme_scenarios:
                self._set_car_and_transit_vdfs()
                self._calc_background_traffic(include_trucks=True)
            self._assign_cars(
                self.stopping_criteria["coarse"],lightweight=True)
            self._calc_extra_wait_time()
            self._assign_transit()
        elif iteration=="last":
            self._set_bike_vdfs()
            self._assign_bikes(self.emme_matrices["bike"]["dist"], "all")
            self._set_car_and_transit_vdfs()
            self._calc_background_traffic()
            self._assign_cars(self.stopping_criteria["fine"])
            self._calc_boarding_penalties(is_last_iteration=True)
            self._calc_extra_wait_time()
            self._assign_transit()
            self._calc_transit_network_results()
        else:
            raise ValueError("Iteration number not valid")

        mtxs = {imp_type: self._get_matrices(imp_type, iteration=="last")
            for imp_type in ("time", "cost", "dist")}
        # fix the emme path analysis results
        # (dist and cost are zero if path not found but we want it to
        # be the default value 999999)
        for mtx_type in ("cost", "dist"):
            for mtx_class in mtxs[mtx_type]:
                path_not_found = mtxs["time"][mtx_class] > 999999
                mtxs[mtx_type][mtx_class][path_not_found] = 999999
        if iteration == "last":
            for mtx_class in ("trailer_truck", "truck"):
                # toll costs are not applied to freight, but the cost
                # matrix is automatically populated with default values
                # (999999) so we need to manually fill it with zeroes
                path_found = mtxs["time"][mtx_class] <= 999999
                mtxs["cost"][mtx_class][path_found] = 0
        # adjust impedance
        mtxs["time"]["bike"] = mtxs["time"]["bike"].clip(None, 9999.)
        if iteration != "last":
            for ass_cl in ("car_work", "car_leisure"):
                mtxs["cost"][ass_cl] += self.dist_unit_cost * mtxs["dist"][ass_cl]
        return mtxs

    def calc_transit_cost(self, fares: pandas.DataFrame):
        """Insert line costs.
        
        Parameters
        ----------
        fares : pandas.DataFrame
            Transit fare zone specification
        """
        network = self.emme_scenario.get_network()
        penalty_attr = param.line_penalty_attr.replace("us", "data")
        op_attr = param.line_operator_attr.replace("ut", "data")
        for line in network.transit_lines():
            for segment in line.segments():
                segment[param.dist_fare_attr] = (fares["dist"][line[op_attr]]
                                                 * segment.link.length)
                segment[penalty_attr] = segment[param.dist_fare_attr]
            line[param.board_fare_attr] = fares["firstb"][line[op_attr]]
            line[param.board_long_dist_attr] = (line[param.board_fare_attr]
                if line.mode.id in param.long_dist_transit_modes else 0)
        self.emme_scenario.publish_network(network)

    def transit_results_links_nodes(self):
        """
        Calculate and sum transit results to link and nodes.
        """
        network = self.emme_scenario.get_network()
        segres = self._segment_results
        for tc in segres:
            for res in segres[tc]:
                nodeattr = self.extra(tc[:10]+"n_"+param.segment_results[res])
                for segment in network.transit_segments():
                    if res == "transit_volumes":
                        if segment.link is not None:
                            segment.link[self.extra(tc)] += segment[segres[tc][res]]
                    else:
                        segment.i_node[nodeattr] += segment[segres[tc][res]]
        self.emme_scenario.publish_network(network)

    def _set_car_and_transit_vdfs(self):
        log.info("Sets car and transit functions for scenario {}".format(
            self.emme_scenario.id))
        network = self.emme_scenario.get_network()
        delay_attr = param.transit_delay_attr.replace("us", "data")
        car_time_attr = self.extra("car_time")
        transit_modesets = {modes[0]: {network.mode(m) for m in modes[1]}
            for modes in param.transit_delay_funcs}
        main_mode = network.mode(param.main_mode)
        car_mode = network.mode(param.assignment_modes["car_work"])
        park_and_ride_mode = network.mode(param.park_and_ride_mode)
        for link in network.links():
            # Car volume delay function definition
            linktype = link.type % 100
            if link.type > 80 and linktype in param.roadclasses:
                # Car link with standard attributes
                roadclass = param.roadclasses[linktype]
                if link.volume_delay_func != 90:
                    link.volume_delay_func = roadclass.volume_delay_func
                link.data1 = roadclass.lane_capacity
                link.data2 = roadclass.free_flow_speed
            elif linktype in param.custom_roadtypes:
                # Custom car link
                if link.volume_delay_func != 90:
                    link.volume_delay_func = linktype - 90
                for linktype in param.roadclasses:
                    roadclass = param.roadclasses[linktype]
                    if (link.volume_delay_func == roadclass.volume_delay_func
                            and link.data2 > roadclass.free_flow_speed-1):
                        # Find the most appropriate road class
                        break
            else:
                # Link with no car traffic
                link.volume_delay_func = 0
            if self.use_stored_speeds:
                try:
                    link.data2 = (link.length / link[car_time_attr]) * 60
                except ZeroDivisionError:
                    link.data2 = 0

            # Transit function definition
            for modeset in param.transit_delay_funcs:
                # Check that intersection is not empty,
                # hence that mode is active on link
                if transit_modesets[modeset[0]] & link.modes:
                    funcs = param.transit_delay_funcs[modeset]
                    if modeset[0] == "bus":
                        buslane_code = link.type // 100
                        if buslane_code in param.bus_lane_link_codes[self.name]:
                            # Bus lane
                            if (link.num_lanes == 3
                                    and roadclass.num_lanes == ">=3"):
                                roadclass = param.roadclasses[linktype - 1]
                                link.data1 = roadclass.lane_capacity
                            link.volume_delay_func += 5
                            func = funcs["buslane"]
                            try:
                                bus_delay = (param.buslane_delay
                                             / max(roadclass.free_flow_speed, 30))
                            except UnboundLocalError:
                                log.warn("Bus mode on link {}, type {}".format(
                                    link.id, link.type))
                        else:
                            # No bus lane
                            func = funcs["no_buslane"]
                            try:
                                bus_delay = roadclass.bus_delay
                            except UnboundLocalError:
                                log.warn("Bus mode on link {}, type {}".format(
                                    link.id, link.type))
                        for segment in link.segments():
                            segment[delay_attr] = bus_delay
                    else:
                        func = funcs[self.name]
                    break
            for segment in link.segments():
                segment.transit_time_func = func
            if car_mode in link.modes:
                link.modes |= {main_mode, park_and_ride_mode}
            else:
                link.modes -= {main_mode, park_and_ride_mode}
        self.emme_scenario.publish_network(network)

    def _set_bike_vdfs(self):
        log.info("Sets bike functions for scenario {}".format(
            self.emme_scenario.id))
        network = self.emme_scenario.get_network()
        main_mode = network.mode(param.main_mode)
        bike_mode = network.mode(param.bike_mode)
        for link in network.links():
            linktype = link.type % 100
            if linktype in param.roadclasses:
                roadtype = param.roadclasses[linktype].type
            elif linktype in param.custom_roadtypes:
                roadtype = param.custom_roadtypes[linktype]
            else:
                roadtype = None
            if (roadtype == "motorway" and network.mode('f') in link.modes
                    and link["@pyoratieluokka"] == 0):
                # Force bikes on motorways onto separate bikepaths
                link["@pyoratieluokka"] = 3
            try:
                pathclass = param.bikepath_vdfs[int(link["@pyoratieluokka"])]
            except KeyError:
                link.volume_delay_func = 98
            else:
                if link.volume_delay_func == 90:
                    pass
                elif roadtype in pathclass:
                    link.volume_delay_func = pathclass[roadtype]
                else:
                    link.volume_delay_func = pathclass[None]
            if bike_mode in link.modes:
                link.modes |= {main_mode}
            elif main_mode in link.modes:
                link.modes -= {main_mode}
        self.emme_scenario.publish_network(network)

    def _set_emmebank_matrices(self, 
                               matrices: Dict[str,numpy.ndarray], 
                               is_last_iteration: bool):
        """Set matrices in emmebank.

        Bike matrices are added together, so that only one matrix is to be
        assigned. Similarly, transit matrices are added together if not last
        iteration. However, they are placed in the matrix "transit_work" to
        save space.

        Parameters
        ----------
        matrices : dict
            Assignment class (car_work/transit/...) : numpy 2-d matrix
        is_last_iteration : bool
            Whether this is the end (multiclass congested transit) assignment
        """
        tmp_mtx = {
            "bike": 0,
        }
        if not is_last_iteration:
            tmp_mtx["transit"] = 0
        for mtx in matrices:
            mode = mtx.split('_')[0]
            if mode in tmp_mtx:
                tmp_mtx[mode] += matrices[mtx]
                if mode == "transit":
                    self._set_matrix("transit_work", tmp_mtx[mode])
                else:
                    self._set_matrix(mode, tmp_mtx[mode])
            else:
                self._set_matrix(mtx, matrices[mtx])

    def _set_matrix(self,
                    ass_class: str,
                    matrix: numpy.ndarray,
                    matrix_type: Optional[str] = "demand"):
        if numpy.isnan(matrix).any():
            msg = ("NAs in demand matrix {} ".format(ass_class)
                   + "would cause infinite loop in Emme assignment.")
            log.error(msg)
            raise ValueError(msg)
        else:
            self.emme_project.modeller.emmebank.matrix(
                self.emme_matrices[ass_class][matrix_type]).set_numpy_data(
                    matrix, scenario_id=self.emme_scenario.id)

    def _get_matrices(self, 
                      mtx_type: str, 
                      is_last_iteration: bool=False) -> Dict[str,numpy.ndarray]:
        """Get all matrices of specified type.

        Parameters
        ----------
        mtx_type : str
            Type (demand/time/transit/...)
        is_last_iteration : bool (optional)
            If this is the last iteration, all matrices are returned,
            otherwise freight impedance matrices are skipped

        Return
        ------
        dict
            Subtype (car_work/truck/inv_time/...) : numpy 2-d matrix
                Matrix of the specified type
        """
        last_iter_classes = param.freight_classes + ("transit_leisure",)
        matrices = {}
        for ass_class, mtx_types in self.emme_matrices.items():
            if (mtx_type in mtx_types and
                    (is_last_iteration or ass_class not in last_iter_classes)):
                if mtx_type == "time" and ass_class in param.assignment_modes:
                    mtx = self._extract_timecost_from_gcost(ass_class)
                elif mtx_type == "time" and ass_class in param.transit_classes:
                    mtx = self._extract_transit_time_from_gcost(ass_class)
                else:
                    mtx = self._get_matrix(ass_class, mtx_type)
                matrices[ass_class] = mtx
        if not is_last_iteration:
            matrices["transit_leisure"] = matrices["transit_work"]
        return matrices

    def _get_matrix(self, 
                    ass_class: str, 
                    matrix_type: str) -> numpy.ndarray:
        """Get matrix with type pair (e.g., demand, car_work).

        Parameters
        ----------
        ass_class : str
            Assignment class (car_work/transit_leisure/truck/...)
        matrix_type : str
            Type (demand/time/cost/...)

        Return
        ------
        numpy 2-d matrix
            Matrix of the specified type
        """
        emme_id = self.emme_matrices[ass_class][matrix_type]
        return (self.emme_project.modeller.emmebank.matrix(emme_id)
                .get_numpy_data(scenario_id=self.emme_scenario.id))

    def _extract_timecost_from_gcost(self, ass_class: str) -> numpy.ndarray:
        """Remove monetary cost from generalized cost.

        Traffic assignment produces a generalized cost matrix.
        To get travel time, monetary cost is removed from generalized cost.
        """
        vot_inv = param.vot_inv[param.vot_classes[ass_class]]
        gcost = self._get_matrix(ass_class, "gen_cost")
        cost = self._get_matrix(ass_class, "cost")
        dist = self._get_matrix(ass_class, "dist")
        if ass_class in ("trailer_truck", "truck"):
            # toll costs are not applied to freight
            time = gcost - vot_inv*param.freight_dist_unit_cost[ass_class]*dist
        else:
            time = gcost - vot_inv*(cost + self.dist_unit_cost*dist)
        self._set_matrix(ass_class, time, "time")
        return time

    def _extract_transit_time_from_gcost(self,
            transit_class: str) -> numpy.ndarray:
        """Remove monetary cost from generalized cost.

        Transit assignment produces a generalized cost matrix.
        To get travel time, monetary cost is removed from generalized cost.
        """
        vot_inv = param.vot_inv[param.vot_classes[transit_class]]
        boards = self._get_matrix(transit_class, "avg_boardings") > 0
        transfer_penalty = boards * param.transfer_penalty[transit_class]
        gcost = self._get_matrix(transit_class, "gen_cost")
        cost = (self._get_matrix(transit_class, "cost")
                + self._get_matrix(transit_class, "actual_total_boarding_costs"))
        time = self._get_matrix(transit_class, "time")
        path_found = cost < 999999
        time[path_found] = (gcost[path_found]
                            - vot_inv*cost[path_found]
                            - transfer_penalty[path_found])
        self._set_matrix(transit_class, time, "time")
        self._set_matrix(transit_class, cost, "cost")
        return time

    def _calc_background_traffic(self, include_trucks: bool = False):
        """Calculate background traffic (buses)."""
        network = self.emme_scenario.get_network()
        # emme api has name "data3" for ul3
        background_traffic = param.background_traffic_attr.replace(
            "ul", "data")
        # calc @bus and data3
        heavy = (self.extra("truck"), self.extra("trailer_truck"))
        park_and_ride = [self._park_and_ride_results[direction]
            for direction in param.park_and_ride_classes]
        for link in network.links():
            if link.type > 100: # If car or bus link
                freq = 0
                for segment in link.segments():
                    segment_hdw = segment.line[self.extra("hdw")]
                    if 0 < segment_hdw < 900:
                        freq += 60 / segment_hdw
                link[self.extra("bus")] = freq
                if link.type // 100 in param.bus_lane_link_codes[self.name]:
                    # Bus lane
                    link[background_traffic] = 0
                else:
                    link[background_traffic] = freq
                for direction in park_and_ride:
                    link[background_traffic] += link[direction]
                if include_trucks:
                    for ass_class in heavy:
                        link[background_traffic] += link[ass_class]
        self.emme_scenario.publish_network(network)

    def _calc_road_cost(self):
        """Calculate road charges and driving costs for one scenario."""
        log.info("Calculates road charges for time period {}...".format(self.name))
        network = self.emme_scenario.get_network()
        for link in network.links():
            toll_cost = link.length * link[self.extra("hinta")]
            dist_cost = self.dist_unit_cost * link.length
            link[self.extra("toll_cost")] = toll_cost
            link[self.extra("total_cost")] = toll_cost + dist_cost
        self.emme_scenario.publish_network(network)

    def _calc_boarding_penalties(self, 
                                 extra_penalty: int = 0, 
                                 is_last_iteration: bool = False):
        """Calculate boarding penalties for transit assignment."""
        # Definition of line specific boarding penalties
        network = self.emme_scenario.get_network()
        if is_last_iteration:
            penalties = param.last_boarding_penalty
        else:
            penalties = param.boarding_penalty
        missing_penalties = set()
        penalty_attr = param.boarding_penalty_attr
        for line in network.transit_lines():
            try:
                penalty = penalties[line.mode.id] + extra_penalty
            except KeyError:
                penalty = extra_penalty
                missing_penalties.add(line.mode.id)
            for transit_class, transfer_pen in param.transfer_penalty.items():
                line[penalty_attr + transit_class] = penalty + transfer_pen
        if missing_penalties:
            missing_penalties_str: str = ", ".join(missing_penalties)
            log.warn("No boarding penalty found for transit modes " + missing_penalties_str)
        self.emme_scenario.publish_network(network)

    def _specify(self):
        self._car_spec = CarSpecification(self.extra, self.emme_matrices)
        self._transit_specs = {tc: TransitSpecification(
                tc, self._segment_results[tc], self._park_and_ride_results[tc],
                param.effective_headway_attr, self.emme_matrices[tc])
            for tc in param.transit_classes}
        self.bike_spec = {
            "type": "STANDARD_TRAFFIC_ASSIGNMENT",
            "classes": [
                {
                    "mode": param.main_mode,
                    "demand": self.emme_matrices["bike"]["demand"],
                    "results": {
                        "od_travel_times": {
                            "shortest_paths": self.emme_matrices["bike"]["time"],
                        },
                        "link_volumes": None, # This is defined later
                    },
                    "analysis": {
                        "results": {
                            "od_values": None, # This is defined later
                        },
                    },
                }
            ],
            "path_analysis": PathAnalysis("ul3").spec,
            "stopping_criteria": {
                "max_iterations": 1,
                "best_relative_gap": 1,
                "relative_gap": 1,
                "normalized_gap": 1,
            },
            "performance_settings": param.performance_settings
        }
        self.walk_spec = {
            "type": "STANDARD_TRANSIT_ASSIGNMENT",
            "modes": param.aux_modes,
            "demand": self.emme_matrices["bike"]["demand"],
            "waiting_time": {
                "headway_fraction": 0.01,
                "effective_headways": "hdw",
                "perception_factor": 0,
            },
            "boarding_time": {
                "penalty": 0,
                "perception_factor": 0,
            },
            "aux_transit_time": {
                "perception_factor": 1,
            },
            "od_results": {
                "transit_times": self.emme_matrices["walk"]["time"],
            },
            "strategy_analysis": {
                "sub_path_combination_operator": "+",
                "sub_strategy_combination_operator": "average",
                "trip_components": {
                    "aux_transit": "length",
                },
                "selected_demand_and_transit_volumes": {
                    "sub_strategies_to_retain": "ALL",
                    "selection_threshold": {
                        "lower": None,
                        "upper": None,
                    },
                },
                "results": {
                    "od_values": self.emme_matrices["walk"]["dist"],
                },
            },
        }

    def _assign_cars(self, 
                     stopping_criteria: Dict[str, Union[int, float]], 
                     lightweight: bool=False):
        """Perform car_work traffic assignment for one scenario."""
        log.info("Car assignment started...")
        car_spec = self._car_spec.spec(lightweight)
        car_spec["stopping_criteria"] = stopping_criteria
        assign_report = self.emme_project.car_assignment(
            car_spec, self.emme_scenario)
        network = self.emme_scenario.get_network()
        time_attr = self.extra("car_time")
        for link in network.links():
            link[time_attr] = link.auto_time
        self.emme_scenario.publish_network(network)
        log.info("Car assignment performed for scenario {}".format(
            self.emme_scenario.id))
        log.info("Stopping criteria: {}, iteration {} / {}".format(
            assign_report["stopping_criterion"],
            len(assign_report["iterations"]),
            stopping_criteria["max_iterations"]
            ))
        if assign_report["stopping_criterion"] == "MAX_ITERATIONS":
            log.warn("Car assignment not fully converged.")
    
    def _assign_bikes(self, 
                      length_mat_id: Union[float, int, str], 
                      length_for_links: str):
        """Perform bike traffic assignment for one scenario.???TYPES"""
        scen = self.emme_scenario
        spec = self.bike_spec
        spec["classes"][0]["results"]["link_volumes"] = self.extra("bike")
        spec["classes"][0]["analysis"]["results"]["od_values"] = length_mat_id
        # Reset ul3 to zero
        netw_spec = {
            "type": "NETWORK_CALCULATION",
            "selections": {
                "link": "all",
            },
            "expression": "0",
            "result": spec["path_analysis"]["link_component"],
            "aggregation": None,
        }
        self.emme_project.network_calc(netw_spec, scen)
        # Define for which links to calculate length and save in ul3
        netw_spec = {
            "type": "NETWORK_CALCULATION",
            "selections": {
                "link": length_for_links,
            },
            "expression": "length",
            "result": spec["path_analysis"]["link_component"],
            "aggregation": None,
        }
        self.emme_project.network_calc(netw_spec, scen)
        log.info("Bike assignment started...")
        self.emme_project.bike_assignment(
            specification=spec, scenario=scen)
        log.info("Bike assignment performed for scenario " + str(scen.id))

    def _assign_pedestrians(self):
        """Perform pedestrian assignment for one scenario."""
        log.info("Pedestrian assignment started...")
        self.emme_project.pedestrian_assignment(
            specification=self.walk_spec, scenario=self.emme_scenario)
        log.info("Pedestrian assignment performed for scenario " + str(self.emme_scenario.id)) 

    def _calc_extra_wait_time(self):
        """Calculate extra waiting time for one scenario."""
        network = self.emme_scenario.get_network()
        log.info("Calculates effective headways "
                 + "and cumulative travel times for scenario "
                 + str(self.emme_scenario.id))
        headway_attr = self.extra("hdw")
        effective_headway_attr = param.effective_headway_attr.replace(
            "ut", "data")
        delay_attr = param.transit_delay_attr.replace("us", "data")
        func = param.effective_headway
        for line in network.transit_lines():
            hw = line[headway_attr]
            for interval in func:
                if interval[0] <= hw < interval[1]:
                    effective_hw = func[interval](hw - interval[0])
                    break
            line[effective_headway_attr] = effective_hw
            cumulative_length = 0
            cumulative_time = 0
            cumulative_speed = 0
            headway_sd = 0
            for segment in line.segments():
                if segment.dwell_time >= 2:
                    # Time-point stops reset headway deviation
                    cumulative_length = 0
                    cumulative_time = 0
                cumulative_length += segment.link.length
                # Travel time for buses in mixed traffic
                if segment.transit_time_func == 1:
                    cumulative_time += (segment.link.auto_time
                                        + segment.dwell_time)
                # Travel time for buses on bus lanes
                if segment.transit_time_func == 2:
                    cumulative_time += (segment.link.length/segment.link.data2
                                        * 60
                                        + segment.dwell_time)
                # Travel time for trams AHT
                if segment.transit_time_func == 3:
                    speedstr = str(int(segment.link.data1))
                    # Digits 5-6 from end (1-2 from beg.) represent AHT
                    # speed. If AHT speed is less than 10, data1 will 
                    # have only 5 digits.
                    speed = int(speedstr[:-4])
                    cumulative_time += ((segment.link.length / speed) * 60
                                        + segment.dwell_time)
                # Travel time for trams PT
                if segment.transit_time_func == 4:
                    speedstr = str(int(segment.link.data1))
                    # Digits 3-4 from end represent PT speed.
                    speed = int(speedstr[-4:-2])
                    cumulative_time += ((segment.link.length / speed) * 60
                                        + segment.dwell_time)
                # Travel time for trams IHT
                if segment.transit_time_func == 5:
                    speedstr = str(int(segment.link.data1))
                    # Digits 1-2 from end represent IHT speed.
                    speed = int(speedstr[-2:])
                    cumulative_time += ((segment.link.length / speed) * 60
                                        + segment.dwell_time)
                # Travel time for rail
                if segment.transit_time_func == 6:
                    cumulative_time += segment[delay_attr] + segment.dwell_time
                if cumulative_time > 0:
                    cumulative_speed = (cumulative_length
                                        / cumulative_time
                                        * 60)
                # Headway standard deviation for buses and trams
                if line.mode.id in param.headway_sd_func:
                    b = param.headway_sd_func[line.mode.id]
                    headway_sd = (b["asc"]
                                  + b["ctime"]*cumulative_time
                                  + b["cspeed"]*cumulative_speed)
                # Estimated waiting time addition caused by headway deviation
                segment["@wait_time_dev"] = (headway_sd**2
                                             / (2.0*line[effective_headway_attr]))
        self.emme_scenario.publish_network(network)

    def _assign_transit(self):
        """Perform transit assignment for one scenario."""
        log.info("Transit assignment started...")
        for i, transit_class in enumerate(param.transit_classes):
            spec = self._transit_specs[transit_class]
            self.emme_project.transit_assignment(
                specification=spec.transit_spec, scenario=self.emme_scenario,
                add_volumes=i, save_strategies=True, class_name=transit_class)
            self.emme_project.matrix_results(
                spec.transit_result_spec, scenario=self.emme_scenario,
                class_name=transit_class)
        log.info("Transit assignment performed for scenario {}".format(
            str(self.emme_scenario.id)))

    def _calc_transit_network_results(self):
        """Calculate transit network results for one scenario."""
        log.info("Calculates transit network results")
        specs = self._transit_specs
        for tc in specs:
            self.emme_project.network_results(
                specs[tc].ntw_results_spec, scenario=self.emme_scenario,
                class_name=tc)
        volax_attr = self.extra("aux_transit")
        network = self.emme_scenario.get_network()
        for link in network.links():
            link[volax_attr] = link.aux_transit_volume
        self.emme_scenario.publish_network(network)
