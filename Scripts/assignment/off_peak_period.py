from typing import Dict, Iterable
from numpy import ndarray
import copy

from assignment.assignment_period import AssignmentPeriod
from assignment.long_dist_period import WholeDayPeriod
from assignment.datatypes.transit import TransitMode
import parameters.assignment as param


class OffPeakPeriod(AssignmentPeriod):
    """Off-peak assignment period.

    The major difference compared to a regular assignment period is that
    bus speeds are taken from free-flow assignment in demand-calculation loop
    and transit assignment is hence not iterated.

    Car assignment is performed as usual.
    """

    def prepare(self, dist_unit_cost: Dict[str, float],
                day_scenario: int, save_matrices: bool):
        """Prepare network for assignment.

        Calculate road toll cost and specify car assignment.
        Set boarding penalties and attribute names.

        Parameters
        ----------
        dist_unit_cost : dict
            key : str
                Assignment class (car_work/truck/...)
            value : float
                Length multiplier to calculate link cost
        day_scenario : int
            EMME scenario linked to the whole day
        save_matrices : bool
            Whether matrices will be saved in Emme format for all time periods.
        """
        self._prepare_cars(dist_unit_cost, save_matrices)
        self._prepare_other(day_scenario, save_matrices)

    def _prepare_other(self, day_scenario: Dict[str, float],
                       save_matrices: bool):
        self._prepare_walk_and_bike(save_matrices=False)
        long_dist_transit_modes = {mode: TransitMode(
                mode, self, day_scenario, save_matrices, save_matrices)
            for mode in param.long_distance_transit_classes}
        self.assignment_modes.update(long_dist_transit_modes)
        self._prepare_transit(
            day_scenario, save_standard_matrices=True,
            save_extra_matrices=save_matrices,
            transit_classes=param.local_transit_classes)

    def init_assign(self):
        """Assign transit for one time period with free-flow bus speed."""
        self._set_car_vdfs(use_free_flow_speeds=True)
        stopping_criteria = copy.copy(
            param.stopping_criteria["coarse"])
        stopping_criteria["max_iterations"] = 0
        self._assign_cars(stopping_criteria)
        self._assign_transit(param.local_transit_classes)
        return []

    def get_soft_mode_impedances(self):
        return []

    def assign(self, *args) -> Dict[str, Dict[str, ndarray]]:
        """Assign cars for one time period.

        Get travel impedance matrices for one time period from assignment.
        Transit impedance is fetched from free-flow init assignment.

        Returns
        -------
        dict
            Type (time/cost/dist) : dict
                Assignment class (car_work/transit/...) : numpy 2-d matrix
        """
        if not self._separate_emme_scenarios:
            self._calc_background_traffic(include_trucks=True)
        self._assign_cars(self.stopping_criteria["coarse"])
        mtxs = self._get_impedances(
            param.car_classes + param.local_transit_classes)
        del mtxs["dist"]
        del mtxs["toll_cost"]
        return mtxs


class TransitAssignmentPeriod(OffPeakPeriod):
    """Transit-only assignment period.

    The major difference compared to a regular assignment period is that
    bus speeds are taken from free-flow assignment and transit assignment
    is hence not iterated.

    Car assignment is not performed at all.
    """
    def __init__(self, *args, **kwargs):
        AssignmentPeriod.__init__(self, *args, **kwargs)
        self.transport_classes = param.local_transit_classes
        self._end_assignment_classes -= set(
            param.private_classes + param.truck_classes)


    def prepare(self, dist_unit_cost: Dict[str, float],
                day_scenario: int, save_matrices: bool):
        """Prepare network for assignment.

        Calculate road toll cost and specify car assignment.
        Set boarding penalties and attribute names.

        Parameters
        ----------
        dist_unit_cost : dict
            key : str
                Assignment class (car_work/truck/...)
            value : float
                Length multiplier to calculate link cost
        day_scenario : int
            EMME scenario linked to the whole day
        save_matrices : bool
            Whether matrices will be saved in Emme format for all time periods.
        """
        self._prepare_cars(
            dist_unit_cost, save_matrices=False, car_classes=["car_leisure"],
            truck_classes=[])
        self._prepare_other(day_scenario, save_matrices)

    def assign_trucks_init(self):
        pass

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
        self._assign_transit(param.transit_classes)
        self._calc_transit_network_results()
        mtxs = self._get_impedances(self._end_assignment_classes)
        for tc in self.assignment_modes:
            self.assignment_modes[tc].release_matrices()
        return mtxs


class EndAssignmentOnlyPeriod(AssignmentPeriod):
    def assign(self, *args) -> None:
        return None
