import pandas
import numpy # type: ignore

from parameters.zone import tour_length_intervals as intervals


class TourLengthHistogram:
    _u = numpy.array(intervals[1:])

    def __init__(self, name):
        index = pandas.MultiIndex.from_tuples(
            zip(intervals[:-1] + ("total",), intervals[1:] + ("kms",)))
        self.histogram = pandas.concat(
            {name: pandas.Series(0.0, index, name="nr_tours")})

    def add(self, dist):
        self.histogram.iat[numpy.searchsorted(self._u, dist, "right")] += 1
        self.histogram.iat[-1] += dist

    def count_tour_dists(self, tours, dists):
        self.histogram.iloc[:-1], _ = numpy.histogram(
            dists, intervals, weights=tours)
        self.histogram.iat[-1] = (dists * tours).sum()
