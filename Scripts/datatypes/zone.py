import numpy
import pandas
from typing import Union, Dict


class ZoneAggregations:
    """Object containing different zone mappings which can be used for
	aggregating data.
    """

    def __init__(self, mappings: pandas.DataFrame,
                 municipality_centre_mapping: pandas.Series):
        """Initialize mappings.

        Parameters
        ----------
        mapping : pandas.Dataframe
            Zone numbers as index and different zone mappings as columns
        municipality_centre_mapping : pandas.Series
            Mapping between zone id and municipality centre index
        """
        self.mappings = mappings
        self.municipality_mapping = mappings.groupby(
            "municipality").agg("first")["county"]
        self.municipality_centre_mapping = municipality_centre_mapping

    def averages(self,
                 array: pandas.Series,
                 weights: pandas.Series,
                 area_type: str) -> pandas.Series:
        """Get weighted area averages.

        Parameters
        ----------
        array : pandas.Series
            Array to average over areas
        weights : pandas.Series
            Array of weights
        area_type : str
            Name of the mapping to use for aggregation

        Returns
        -------
        pandas.Series
            Aggregated array
        """
        avg = lambda a, w: numpy.ma.average(a, weights=w[a.index])
        agg = array.groupby(self.mappings[area_type]).agg(avg, w=weights)
        agg["all"] = avg(array, weights)
        return agg

    def aggregate_mtx(self,
                      matrix: pandas.DataFrame,
                      area_type: str) -> pandas.DataFrame:
        """Aggregate (tour demand) matrix to larger areas.

        Parameters
        ----------
        matrix : pandas.DataFrame
            Disaggregated matrix with zone indices and columns
        area_type : str
            Name of the mapping to use for aggregation

        Returns
        -------
        pandas.DataFrame
            Matrix aggregated to the selected mapping
        """
        return self.aggregate_array(
            self.aggregate_array(matrix, area_type).T, area_type)

    def aggregate_array(self,
                        array: Union[pandas.Series, pandas.DataFrame],
                        area_type: str) -> Union[pandas.Series, pandas.DataFrame]:
        """Aggregate (tour demand) array to larger areas.

        Parameters
        ----------
        array : pandas.Series
            Disaggregated array with zone indices
        area_type : str
            Name of the mapping to use for aggregation

        Returns
        -------
        pandas.Series
            Array aggregated to the selected mapping
        """
        return array.groupby(self.mappings[area_type]).agg("sum")


class Zone:
    counter = 0

    def __init__(self, number: int, aggregations: ZoneAggregations):
        self.number = number
        self.index = Zone.counter
        Zone.counter += 1
        self.area = aggregations.mappings["area"][number]
        self.municipality = aggregations.mappings["municipality"][number]
