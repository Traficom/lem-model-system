from __future__ import annotations
from typing import Any, Dict, List, Sequence, Optional, Union
from pathlib import Path
import numpy # type: ignore
import pandas
import fiona
import logging
import json

import parameters.zone as param
from utils.read_csv_file import read_other_data
import utils.log as log
from datatypes.zone import Zone, ZoneAggregations


class ZoneData:
    """Container for zone data read from input files.

    Parameters
    ----------
    data_dir : Path
        Directory where scenario input data files are found
    zone_numbers : list
        Zone numbers to compare with for validation
    zone_mapping : str
            Name of column where mapping between data zones (index)
            and assignment zones
    """
    def __init__(self, data_dir: Path, zone_numbers: Sequence,
                 zone_mapping: str):
        self.transit_zone = read_other_data(data_dir / "transit_cost.tsv")
        try:
            self.mtx_adjustment = read_other_data(
                data_dir / "matrix_adjustment.tsv")
        except (NameError, KeyError):
            self.mtx_adjustment = None
        car_cost = read_other_data(data_dir / "car_cost.tsv")
        self.car_dist_cost = car_cost["dist_cost"].to_dict()
        self._values = {}
        self.share = ShareChecker(self)
        all_zone_numbers = numpy.array(zone_numbers)
        self.all_zone_numbers = all_zone_numbers
        peripheral = param.purpose_areas["peripheral"]
        self.zone_numbers = pandas.Index(
            all_zone_numbers[:all_zone_numbers.searchsorted(peripheral[1])],
            name="analysis_zone_id")
        Zone.counter = 0
        data, mapping = read_zonedata(
            data_dir / "zonedata.gpkg", self.zone_numbers, zone_mapping)
        self.mapping = mapping
        zone_indices = pandas.Series(
            range(len(self.zone_numbers)), index=self.zone_numbers)
        agg_keys = [key for key in data if "aggregate_results_" in key]
        aggs = data[agg_keys].rename(
            columns=lambda x : x.replace("aggregate_results_", ""))
        self.aggregations = ZoneAggregations(
            aggs, data["municipality_center"].map(zone_indices))
        self.zones = {number: Zone(number, self.aggregations)
            for number in self.zone_numbers}
        self.share["share_female"] = pandas.Series(
            0.5, self.zone_numbers, dtype=numpy.float32)
        self.share["share_male"] = pandas.Series(
            0.5, self.zone_numbers, dtype=numpy.float32)
        share_7_99 = pandas.Series(0, self.zone_numbers, dtype=numpy.float32)
        pop = data["population"]
        wp = data["workplaces"]
        for col in data:
            if col not in agg_keys:
                self[col] = data[col]
            if col.startswith("sh_age"):
                pop_share = data[col]
                self.share[col] = pop_share
                col_name = col.replace("sh_", "")
                self[col_name] = pop_share * pop
                self[col_name + "_female"] = 0.5 * pop_share * pop
                self[col_name + "_male"] = 0.5 * pop_share * pop
                share_7_99 += pop_share
            if col.startswith("sh_income"):
                self[col.replace("sh_", "")] = data[col] * pop
            if col.startswith("sh_wrk_"):
                self[col.replace("sh_wrk_", "")] = data[col] * wp
        self.share["share_age_7-99"] = share_7_99
        self.nr_zones = len(self.zone_numbers)
        # Create diagonal matrix with zone area
        self["within_zone"] = numpy.full((self.nr_zones, self.nr_zones), 0.0)
        self["within_zone"][numpy.diag_indices(self.nr_zones)] = 1.0
        # Two-way intrazonal distances from building distances
        self["within_zone_dist"] = (self["within_zone"] 
                                    * data["avg_building_distance"].values * 2)
        self["within_zone_time"] = self["within_zone_dist"] / (20/60) # 20 km/h
        self["within_zone_cost"] = (self["within_zone_dist"]
                                    * self.car_dist_cost["car_work"])
        # Unavailability of intrazonal tours
        self["within_zone_inf"] = numpy.full((self.nr_zones, self.nr_zones), 0.0)
        self["within_zone_inf"][numpy.diag_indices(self.nr_zones)] = numpy.inf
        # Create matrix where value is True if origin and destination is in
        # same municipality
        municipalities = self.aggregations.mappings["municipality"].values
        within_municipality = municipalities[:, numpy.newaxis] == municipalities
        self["within_municipality"] = within_municipality
        self["outside_municipality"] = ~within_municipality
        for dummy in ("Helsingin_kantakaupunki", "Tampereen_kantakaupunki"):
            self[dummy] = self.dummy("subarea", dummy)
        for key in data["aggregate_results_submodel"].unique():
            self["population_" + key] = self.dummy("submodel", key) * pop

    def dummy(self, division_type, name, bounds=slice(None)):
        dummy = self.aggregations.mappings[division_type][bounds] == name
        return dummy

    @property
    def zone_values(self):
        return {key: val for key, val in self._values.items()
            if isinstance(val, pandas.Series)}

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key: str, data: Any):
        try:
            if not numpy.isfinite(data).all():
                for (i, val) in data.iteritems():
                    if not numpy.isfinite(val):
                        msg = "{} for zone {} is not a finite number".format(
                            key, i).capitalize()
                        log.error(msg)
                        raise ValueError(msg)
        except TypeError:
            for (i, val) in data.iteritems():
                try:
                    float(val)
                except ValueError:
                    msg = "{} for zone {} is not a number".format(
                        key, i).capitalize()
                    log.error(msg)
                    raise TypeError(msg)
            msg = "{} could not be read".format(key).capitalize()
            log.error(msg)
            raise TypeError(msg)
        if (data < 0).any():
            for (i, val) in data.iteritems():
                if val < 0:
                    msg = "{} ({}) for zone {} is negative".format(
                        key, val, i).capitalize()
                    log.error(msg)
                    raise ValueError(msg)
        self._values[key] = data.astype(numpy.float32)

    def zone_index(self, 
                   zone_number: int) -> int:
        """Get index of given zone number.

        Parameters
        ----------
        zone_number : int
            The zone number to look up
        
        Returns
        -------
        int
            Index of zone number
        """
        return self.zones[zone_number].index

    def get_data(self, key: str, bounds: slice, generation: bool=False) -> Union[pandas.Series, numpy.ndarray]:
        """Get data of correct shape for zones included in purpose.
        
        Parameters
        ----------
        key : str
            Key describing the data (e.g., "population")
        bounds : slice
            Slice that describes the lower and upper bounds of purpose
        generation : bool, optional
            If set to True, returns data only for zones in purpose,
            otherwise returns data for all zones
        
        Returns
        -------
        pandas Series or numpy 2-d matrix
        """
        try:
            val = self._values[key]
        except KeyError as err:
            keyl: List[str] = key.split('<')
            if keyl[1] in ("within_municipality", "outside_municipality"):
                # If parameter is only for own municipality or for all
                # municipalities except own, array is multiplied by
                # bool matrix
                return (self[keyl[1]] * self._values[keyl[0]].values)[bounds, :]
            else:
                raise KeyError(err)
        if val.ndim == 1: # If not a compound (i.e., matrix)
            if generation:  # Return values for purpose zones
                return val[bounds].values
            else:  # Return values for all zones
                return val.values
        else:  # Return matrix (purpose zones -> all zones)
            return val[bounds, :]


class ShareChecker:
    def __init__(self, data):
        self.data = data

    def __setitem__(self, key, data):
        if (data > 1.02).any():
            for (i, val) in data.iteritems():
                if val > 1.02:
                    msg = "{} ({}) for zone {} is larger than one".format(
                        key, val, i).capitalize()
                    log.error(msg)
                    raise ValueError(msg)
        self.data[key] = data

def read_zonedata(path: Path,
                  zone_numbers: numpy.ndarray,
                  zone_mapping_name: str):
    """Read zone data from space-separated file.

    Parameters
    ----------
    path : Path
        Path to the .gpkg file
    zone_numbers : ndarray
        Zone numbers to compare with for validation
    zone_mapping_name : str
        Name of column where mapping between data zones (index)
        and assignment zones

    Returns
    -------
    pandas.DataFrame
        Zone data
    pandas.Series
        Mapping between zones in zone-data file and in network
    """
    if not path.exists():
        msg = f"Path {path} not found."
        raise NameError(msg)
    logging.getLogger("fiona").setLevel(logging.ERROR)
    with fiona.open(path, ignore_geometry=True) as colxn:
        data = pandas.DataFrame(
            [record["properties"] for record in colxn],
            columns=list(colxn.schema["properties"]))
    data.set_index("input_zone_id", inplace=True)
    if data.index.hasnans:
        msg = "Row with only spaces or tabs in file {}".format(path)
        log.error(msg)
        raise IndexError(msg)
    if data.index.has_duplicates:
        raise IndexError("Index in file {} has duplicates".format(path))
    if not data.index.is_monotonic_increasing:
        data.sort_index(inplace=True)
        log.warn("File {} is not sorted in ascending order".format(path))
    zone_mapping = data[zone_mapping_name]
    zone_variables = json.loads(
        (Path(__file__).parent / "zone_variables.json").read_text("utf-8"))
    aggs = {}
    for func, cols in zone_variables.items():
        for col in cols:
            try:
                total = col["total"]
            except TypeError:
                aggs[col] = func
            else:
                aggs[total] = func
                for share in col["shares"]:
                    aggs[share] = lambda x: avg(x, weights=data[total])
    data = data.groupby(zone_mapping_name).agg(aggs)
    data.index = data.index.astype(int)
    data.index.name = "analysis_zone_id"
    if data.index.size != zone_numbers.size or (data.index != zone_numbers).any():
        for i in data.index:
            if int(i) not in zone_numbers:
                msg = (f"Zone number {i} from mapping {data.index.name} "
                       + f"in file {path} not found in network")
                log.error(msg)
                raise IndexError(msg)
        for i in zone_numbers:
            if i not in data.index:
                msg = (f"Zone number {i} not found in mapping "
                       + f"{data.index.name} in file {path}")
                log.error(msg)
                raise IndexError(msg)
        msg = "Zone numbers did not match for file {}".format(path)
        log.error(msg)
        raise IndexError(msg)
    return data, zone_mapping

def avg(data, weights):
    try:
        return numpy.average(data, weights=weights[data.index])
    except ZeroDivisionError:
        return 0
