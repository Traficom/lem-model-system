from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
import numpy # type: ignore
import pandas
if TYPE_CHECKING:
    from datahandling.matrixdata import MatrixData


import utils.log as log
import parameters.assignment as param
import parameters.zone as zone_param
from assignment.abstract_assignment import AssignmentModel, Period


class MockAssignmentModel(AssignmentModel):
    def __init__(self, matrices: MatrixData,
                 use_free_flow_speeds: bool = False,
                 time_periods: List[str]=param.time_periods):
        self.matrices = matrices
        log.info("Reading matrices from " + str(self.matrices.path))
        self.use_free_flow_speeds = use_free_flow_speeds
        self.time_periods = time_periods
        self.assignment_periods = [MockPeriod(tp, matrices)
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

    def calc_transit_cost(self, fare):
        pass

    def aggregate_results(self, resultdata):
        pass

    def calc_noise(self):
        return pandas.Series(0, zone_param.area_aggregation)

    def prepare_network(self, car_dist_unit_cost: Dict[str, float]):
        for ap in self.assignment_periods:
            ap.dist_unit_cost = car_dist_unit_cost

    def init_assign(self):
        pass


class MockPeriod(Period):
    def __init__(self, name: str, matrices: MatrixData):
        self.name = name
        self.matrices = matrices

    @property
    def zone_numbers(self):
        """Numpy array of all zone numbers.""" 
        with self.matrices.open("time", self.name) as mtx:
            zone_numbers = mtx.zone_numbers
        return zone_numbers

    def assign_trucks_init(self):
        pass

    def assign(self) -> Dict[str, Dict[str, numpy.ndarray]]:
        """ Get travel impedance matrices for one time period from files.

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (car_work/transit_leisure/...) : numpy 2-d matrix
        """
        mtxs = self._get_impedances()
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
        return self._get_impedances()

    def _get_impedances(self):
        mtxs = {mtx_type: self._get_matrices(mtx_type)
            for mtx_type in ("time", "cost", "dist")}
        for mode in mtxs["time"]:
            try:
                mtx = numpy.divide(mtxs["dist"][mode], mtxs["time"][mode]/60,
                                   out=numpy.zeros_like(mtxs["time"][mode]), 
                                   where=mtxs["time"][mode]>0)
                v = [round(numpy.quantile(mtx, q)) for q in [0.00, 0.50, 1.00]]
                log.debug(f"Min, median, max of OD speed: {mode} : {v[0]} - {v[1]} - {v[2]} km/h")
            except KeyError:
                pass
        return mtxs

    def _get_matrices(self, mtx_type: str) -> Dict[str, numpy.ndarray]:
        """Get all matrices of specified type.
        
        Parameters
        ----------
        mtx_type : str
            Type (demand/time/transit/...)

        Return
        ------
        dict
            Subtype (car_work/truck/inv_time/...) : numpy 2-d matrix
                Matrix of the specified type
        """
        with self.matrices.open(mtx_type, self.name) as mtx:
            matrices = {mode: mtx[mode] for mode in mtx.matrix_list}
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
