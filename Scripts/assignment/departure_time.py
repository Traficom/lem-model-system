from __future__ import annotations
from typing import Any, Dict, List, Tuple, Union, Sequence, cast
import numpy # type: ignore

from datatypes.demand import Demand
from datatypes.tour import Tour
import utils.log as log
from assignment.abstract_assignment import AssignmentModel
import parameters.departure_time as param
from parameters.assignment import (
   transport_classes, car_classes, long_distance_transit_classes)


class DepartureTimeModel:
    """Container for time period and assignment class specific demand.

    Parameters
    ----------
    nr_zones : int
        Number of zones in assignment model
    time_periods : list of str (optional)
        Time period names, default is aht, pt, iht
    modes : List of str (optional)
            Assignment classes for which initialization is done.
            Default is all assignment classes.
    """
    def __init__(self,
                 nr_zones: int,
                 time_periods: List[str] = list(param.backup_demand_share),
                 modes: Sequence[str] = transport_classes):
        self.nr_zones = nr_zones
        self.time_periods = time_periods
        self.old_car_demand: Union[int,numpy.ndarray] = 0
        self._create_container(modes)
        self.init_demand(modes)

    def calc_gaps(self) -> Dict[str,float]:
        """Calculate two demand convergence indicators.

        Comparing car work demand matrix from previous round to current one.

        Returns
        -------
        dict
            rel_gap : float
                Mean relative gap for car work demand ((new-old)/old)
            max_gap : float
                Maximum gap for OD pair in car work demand matrix
        """
        car_demand = self.demand[next(iter(self.time_periods))]["car_work"]
        max_gap = numpy.abs(car_demand - self.old_car_demand).max()
        try:
            old_sum = self.old_car_demand.sum()
            relative_gap = abs((car_demand.sum()-old_sum) / old_sum)
        except AttributeError:
            relative_gap = 0
        self.old_car_demand = car_demand
        return {"rel_gap": relative_gap, "max_gap": max_gap}

    def _create_container(self, modes: Sequence[str] = transport_classes):
        self.demand = {tp: {tc: 0 for tc in modes if tc in transport_classes}
            for tp in self.time_periods}

    def init_demand(self, modes: Sequence[str] = transport_classes):
        """Initialize/reset demand for all time periods.

        Parameters
        ----------
        modes : List of str (optional)
            Assignment classes for which initialization is done.
            Default is all assignment classes.
        """
        n = self.nr_zones
        for tp in self.time_periods:
            for tc in modes:
                if tc in transport_classes:
                    self.demand[tp][tc] = numpy.zeros((n, n), numpy.float32)

    def add_demand(self, demand: Union[Demand, Tour]):
        """Add demand matrix for whole day.
        
        Parameters
        ----------
        demand : Demand or Tour
            Travel demand matrix or number of travellers
        """
        demand.purpose.name = cast(str, demand.purpose.name) #type checker hint
        if demand.mode in transport_classes:
            position: Sequence[int] = demand.position
            if len(position) == 2:
                share: Dict[str, Any] = demand.purpose.demand_share[demand.mode]
                for time_period in self.time_periods:
                    self._add_2d_demand(
                        share[time_period], demand.mode, time_period,
                        demand.matrix, position)
            elif len(position) == 3:
                for time_period in self.time_periods:
                    self._add_3d_demand(demand, demand.mode, time_period)
            else:
                raise IndexError("Tuple position has wrong dimensions.")

    def _add_2d_demand(self,
                       demand_share: Any,
                       ass_class: str,
                       time_period: str,
                       mtx: numpy.ndarray,
                       mtx_pos: Tuple[int, int]):
        """Slice demand, include transpose and add for one time period. ???types"""
        r_0 = mtx_pos[0]
        c_0 = mtx_pos[1]
        r_n = r_0 + mtx.shape[0]
        c_n = c_0 + mtx.shape[1]
        large_mtx = self.demand[time_period][ass_class]
        try:
            large_mtx[r_0:r_n, c_0:c_n] += demand_share[0] * mtx
            large_mtx[c_0:c_n, r_0:r_n] += demand_share[1] * mtx.T
        except ValueError:
            share = param.backup_demand_share[time_period]
            large_mtx[r_0:r_n, c_0:c_n] += share[0] * mtx
            large_mtx[c_0:c_n, r_0:r_n] += share[1] * mtx.T
            log.warn("{} {} matrix not matching {} demand shares. Resorted to backup demand shares.".format(
                mtx.shape, ass_class, len(demand_share[0])))
        self.demand[time_period][ass_class] = large_mtx

    def _add_3d_demand(self,
                       demand: Union[Demand, Tour],
                       ass_class: str,
                       time_period: str):
        """Add three-way demand."""
        mtx: numpy.ndarray = demand.matrix
        tp: str = time_period
        (o, d1, d2) = demand.position
        share = demand.purpose.demand_share[demand.mode][tp]
        if demand.dest is not None:
            # For agent simulation
            self._add_2d_demand(share, ass_class, tp, mtx, (o, d1))
            share = demand.purpose.sec_dest_purpose.demand_share[demand.mode][tp]
        colsum = mtx.sum(0)[:, numpy.newaxis]
        self._add_2d_demand(share[0], ass_class, tp, mtx, (d1, d2))
        self._add_2d_demand(share[1], ass_class, tp, colsum, (d2, o))
    
    def add_vans(self, time_period: str, nr_zones: int):
        """Add vans as a share of private car trips for one time period.
        
        Parameters
        ----------
        time_period : str
            Time period (aht/pt/iht)
        nr_zones : int
            Number of zones in model area (metropolitan + peripheral)
        """
        n = nr_zones
        mtx = self.demand[time_period]
        car_demand = (mtx["car_work"][0:n, 0:n] + mtx["car_leisure"][0:n, 0:n])
        share = param.demand_share["freight"]["van"][time_period]
        self._add_2d_demand(share, "van", time_period, car_demand, (0, 0))
        self._add_2d_demand(
            (1, 0), "van", time_period, mtx["truck"][0:n, 0:n], (0, 0))


class DirectDepartureTimeModel (DepartureTimeModel):
    def __init__(self, assignment_model: AssignmentModel):
        self._ass_model = assignment_model
        modes = (car_classes + long_distance_transit_classes
            if assignment_model.use_free_flow_speeds else transport_classes)
        DepartureTimeModel.__init__(
            self, assignment_model.nr_zones, assignment_model.time_periods,
            modes)

    def _create_container(self, *args):
        self.demand = {ap.name: EmmeMatrixContainer(ap)
            for ap in self._ass_model.assignment_periods}


class EmmeMatrixContainer:
    def __init__(self, assignment_period) -> None:
        self._assignment_period = assignment_period

    def __getitem__(self, key: str) -> numpy.ndarray:
        return self._assignment_period.get_matrix(key)

    def __setitem__(self, key: str, data: Any):
        self._assignment_period.set_matrix(key, data)
