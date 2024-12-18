import numpy
import pandas
from collections import defaultdict

import parameters.tour_generation as param


class GenerationModel:
    """Container for tour vector.

    Regular tours are created in `model.logit.TourCombinationModel`
    and then added to the `tours` vector for each `TourPurpose`.
    Peripheral tours are calculated directly in `add_tours()`.

    Parameters
    ----------
    purpose : datatypes.purpose.TourPurpose
        Travel purpose (hw/hs/ho/...)
    resultdata : ResultData
        Writer object for result directory
    """

    def __init__(self, purpose, resultdata):
        self.resultdata = resultdata
        self.zone_data = purpose.zone_data
        self.purpose = purpose
        self.param = param.tour_generation[purpose.name]

    def init_tours(self):
        """Initialize `tours` vector to 0."""
        self.tours = pandas.Series(
            0.0, self.purpose.zone_numbers, dtype=numpy.float32)

    def add_tours(self):
        """Generate and add (peripheral) tours to zone vector."""
        b = self.param
        for i in b:
            self.tours += b[i] * self.zone_data[i][self.purpose.bounds]

    def get_tours(self):
        """Get vector of tour numbers per zone.
        
        Return
        ------
        numpy.ndarray
            Vector of tour numbers per zone
        """
        return self.tours.values


class NonHomeGeneration(GenerationModel):
    """For calculating numbers of non-home tours starting in each zone.

    Parameters
    ----------
    purpose : datatypes.purpose.TourPurpose
        Travel purpose (hw/hs/ho/...)
    resultdata : ResultData
        Writer object for result directory
    """

    def add_tours(self):
        pass
    
    def get_tours(self):
        """Generate vector of tour numbers from attracted source tours.

        Assumes that home-based tours have been assigned destinations.
        
        Return
        ------
        numpy.ndarray
            Vector of tour numbers per zone
        """
        mode_tours = defaultdict(float)
        for source in self.purpose.sources:
            b = self.param[source.name]
            for mode in source.attracted_tours:
                mode_tours[mode] += b * source.attracted_tours[mode]
        tours = sum(mode_tours.values())
        for mode in mode_tours:
            key = f"{self.purpose.name}_parent_{mode}_share"
            self.zone_data.share[key] = mode_tours[mode] / tours
        return tours


class SecDestGeneration(GenerationModel):
    """For calculating numbers of secondary-destination tours.

    Calculation is for each mode and origin-destination pair separately.

    Parameters
    ----------
    purpose : datatypes.purpose.TourPurpose
        Travel purpose (hw/hs/ho/...)
    resultdata : ResultData
        Writer object for result directory
    """

    def init_tours(self):
        self.tours = dict.fromkeys(self.purpose.modes)
        for mode in self.tours:
            self.tours[mode] = 0
    
    def add_tours(self, demand, mode, purpose):
        """Generate matrix of tour numbers from attracted source tours."""
        mod_mode = mode.replace("work", "leisure")
        if mod_mode in self.purpose.modes:
            bounds = self.purpose.bounds
            metropolitan = next(iter(self.purpose.sources)).bounds
            self.tours[mod_mode] += (self.param[purpose.name][mode]
                                     * demand[metropolitan, bounds])
    
    def get_tours(self, mode):
        """Get vector of tour numbers per od pair.
        
        Return
        ------
        numpy.ndarray
            Matrix of tour numbers per origin-destination pair
        """
        return self.tours[mode]
