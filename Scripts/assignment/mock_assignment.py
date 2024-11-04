from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Iterable
import numpy # type: ignore
import pandas
if TYPE_CHECKING:
    from datahandling.matrixdata import MatrixData


import utils.log as log
from utils.divide_matrices import divide_matrices
import parameters.assignment as param
import parameters.zone as zone_param
from assignment.abstract_assignment import AssignmentModel, Period


class MockAssignmentModel(AssignmentModel):
    def __init__(self, matrices: MatrixData,
                 use_free_flow_speeds: bool = False,
                 time_periods: List[str]=param.time_periods,
                 delete_extra_matrices: bool = False):
        self.matrices = matrices
        log.info("Reading matrices from " + str(self.matrices.path))
        self.use_free_flow_speeds = use_free_flow_speeds
        end_assignment_classes = set(param.emme_matrices)
        if delete_extra_matrices:
            end_assignment_classes -= set(param.freight_classes)
            if use_free_flow_speeds:
                end_assignment_classes -= set(param.local_transit_classes)
            else:
                end_assignment_classes -= set(
                    param.long_distance_transit_classes)
        self.time_periods = time_periods
        self.assignment_periods = [MockPeriod(
                tp, matrices, end_assignment_classes)
            for tp in time_periods]

    @property
    def zone_numbers(self) -> numpy.array:
        """Numpy array of all zone numbers.""" 
        with self.matrices.open("time", self.time_periods[0]) as mtx:
            zone_numbers = mtx.zone_numbers
        return zone_numbers

    @property
    def mapping(self):
        """dict: Dictionary of zone numbers and corresponding indices."""
        with self.matrices.open("time", self.time_periods[0]) as mtx:
            mapping = mtx.mapping
        return mapping

    @property
    def nr_zones(self) -> int:
        """int: Number of zones in assignment model."""
        return len(self.zone_numbers)

    @property
    def beeline_dist(self):
        with self.matrices.open("beeline", "") as mtx:
            matrix = mtx["all"]
        return matrix

    def calc_transit_cost(self, fare):
        pass

    def aggregate_results(self, resultdata, mapping):
        pass

    def calc_noise(self, mapping):
        return pandas.Series(0.0, mapping.drop_duplicates())

    def prepare_network(self, car_dist_unit_cost: Dict[str, float], *args):
        for ap in self.assignment_periods:
            ap.dist_unit_cost = car_dist_unit_cost

    def init_assign(self):
        pass


class MockPeriod(Period):
    def __init__(self,
                 name: str, matrices: MatrixData,
                 end_assignment_classes: Iterable[str]):
        self.name = name
        self.matrices = matrices
        self._end_assignment_classes = end_assignment_classes

    @property
    def zone_numbers(self):
        """Numpy array of all zone numbers.""" 
        with self.matrices.open("time", self.name) as mtx:
            zone_numbers = mtx.zone_numbers
        return zone_numbers

    def assign_trucks_init(self):
        pass

    def assign(self, modes: Iterable[str]
            ) -> Dict[str, Dict[str, numpy.ndarray]]:
        """ Get travel impedance matrices for one time period from files.

        Parameters
        ----------
        modes : Set of str
            The assignment classes for which impedance matrices will be returned

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (car_work/transit_leisure/...) : numpy 2-d matrix
        """
        mtxs = self._get_impedances(modes)
        for ass_cl in param.car_classes:
            mtxs["cost"][ass_cl] += (self.dist_unit_cost[ass_cl]
                                        * mtxs["dist"][ass_cl])
        return mtxs

    def end_assign(self) -> Dict[str, Dict[str, numpy.ndarray]]:
        """ Get travel impedance matrices for one time period from files.

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (car_work/transit_leisure/...) : numpy 2-d matrix
        """
        return self._get_impedances(self._end_assignment_classes)

    def _get_impedances(self, assignment_classes: Iterable[str]):
        mtxs = {mtx_type: self._get_matrices(mtx_type, assignment_classes)
            for mtx_type in ("time", "cost", "dist")}
        for mode in mtxs["time"]:
            try:
                divide_matrices(
                    mtxs["dist"][mode], mtxs["time"][mode]/60,
                    f"OD speed (km/h) {mode}")
            except KeyError:
                pass
        return mtxs

    def _get_matrices(self,
                      mtx_type: str,
                      assignment_classes: Iterable[str]
            ) -> Dict[str, numpy.ndarray]:
        """Get all matrices of specified type.
        
        Parameters
        ----------
        mtx_type : str
            Type (demand/time/transit/...)
        assignment_classes : Set of str
            The assignment classes for which impedance matrices will be returned

        Return
        ------
        dict
            Subtype (car_work/truck/inv_time/...) : numpy 2-d matrix
                Matrix of the specified type
        """
        matrix_list = [ass_class for ass_class in assignment_classes
            if mtx_type in param.emme_matrices.get(ass_class, [])]
        with self.matrices.open(
                mtx_type, self.name, transport_classes=matrix_list) as mtx:
            matrices = {mode: mtx[mode] for mode in matrix_list}
        for mode in matrices:
            if numpy.any(matrices[mode] > 1e10):
                log.warn(f"Matrix with infinite values: {mtx_type} : {mode}.")
        return matrices

    def get_matrix(self,
                    ass_class: str,
                    matrix_type: str) -> numpy.ndarray:
        with self.matrices.open(matrix_type, self.name) as mtx:
            matrix = mtx[ass_class]
        return matrix

    def set_matrix(self,
                    ass_class: str,
                    matrix: numpy.ndarray):
        with self.matrices.open("demand", self.name, self.zone_numbers, m='a') as mtx:
            mtx[ass_class] = matrix
