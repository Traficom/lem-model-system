from typing import Dict, Iterable
from numpy.core import ndarray
import copy

from assignment.assignment_period import AssignmentPeriod
import parameters.assignment as param


class OffPeakPeriod(AssignmentPeriod):
    """Off-peak assignment period.

    The major difference compared to a regular assignment period is that
    bus speeds are taken from free-flow assignment in demand-calculation loop
    and transit assignment is hence not iterated.

    Car assignment is performed as usual.
    """

    def init_assign(self):
        """Assign transit for one time period with free-flow bus speed."""
        self._set_car_vdfs(use_free_flow_speeds=True)
        stopping_criteria = copy.copy(
            param.stopping_criteria["coarse"])
        stopping_criteria["max_iterations"] = 0
        self._assign_cars(stopping_criteria)
        self._assign_transit(param.transit_classes)

    def assign(self, modes: Iterable[str]) -> Dict[str, Dict[str, ndarray]]:
        """Assign cars for one time period.

        Get travel impedance matrices for one time period from assignment.
        Transit impedance is fetched from free-flow init assignment.

        Parameters
        ----------
        modes : Set of str
            The assignment classes for which impedance matrices will be returned

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (car_work/transit/...) : numpy 2-d matrix
        """
        if not self._separate_emme_scenarios:
            self._calc_background_traffic(include_trucks=True)
        self._assign_cars(self.stopping_criteria["coarse"])
        mtxs = self._get_impedances(modes)
        for ass_cl in param.car_classes:
            mtxs["cost"][ass_cl] += self._dist_unit_cost[ass_cl] * mtxs["dist"][ass_cl]
        del mtxs["dist"]
        return mtxs


class TransitAssignmentPeriod(OffPeakPeriod):
    """Transit-only assignment period.

    The major difference compared to a regular assignment period is that
    bus speeds are taken from free-flow assignment and transit assignment
    is hence not iterated.

    Car assignment is not performed at all.
    """

    def assign(self, *args) -> Dict[str, Dict[str, ndarray]]:
        """Get local transit impedance matrices for one time period.

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (transit_work/transit_leisure) : numpy 2-d matrix
        """
        mtxs = self._get_impedances(param.local_transit_classes)
        del mtxs["dist"]
        return mtxs

    def end_assign(self) -> Dict[str, Dict[str, ndarray]]:
        """Get transit impedance matrices for one time period.

        Long-distance mode impedances are included if assignment period
        was created with delete_extra_matrices option disabled.

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (transit_work/...) : numpy 2-d matrix
        """
        self._calc_transit_network_results()
        self._end_assignment_classes -= set(
            param.private_classes + param.freight_classes)
        return self._get_impedances(self._end_assignment_classes)


class EndAssignmentOnlyPeriod(AssignmentPeriod):
    def assign(self, *args) -> None:
        return None
