from __future__ import annotations
from typing import Any, Dict, List, Sequence, Optional, Union
from pathlib import Path
import numpy # type: ignore
import pandas

import parameters.zone as param
from utils.read_csv_file import FileReader, read_mapping
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
    aggregations : datatypes.zone.ZoneAggregations
        Container for zone aggregations read from input file
    zone_mapping : pandas.Series (optional)
        Mapping between data zones (index) and assignment zones
    """
    def __init__(self, data_dir: Path, zone_numbers: Sequence,
                 aggregations: ZoneAggregations,
                 zone_mapping: Optional[pandas.Series] = None):
        self.aggregations = aggregations
        self._values = {}
        self.share = ShareChecker(self)
        all_zone_numbers = numpy.array(zone_numbers)
        self.all_zone_numbers = all_zone_numbers
        peripheral = param.purpose_areas["peripheral"]
        external = param.purpose_areas["external"]
        self.zone_numbers = pandas.Index(
            all_zone_numbers[:all_zone_numbers.searchsorted(peripheral[1])],
            name="zone_id")
        Zone.counter = 0
        self.zones = {number: Zone(number, aggregations) for number in self.zone_numbers}
        files = FileReader(
            data_dir, self.zone_numbers, numpy.float32, zone_mapping)
        popdata = files.read_csv_file(".pop")
        workdata = files.read_csv_file(".wrk")
        incdata = files.read_csv_file(".inc")
        schooldata = files.read_csv_file(".edu")
        parkdata = files.read_csv_file(".prk")
        sport_facilities = files.read_csv_file(".spo")
        buildings = files.read_csv_file(".bld")
        files = FileReader(data_dir)
        self.transit_zone = files.read_csv_file(".tco")
        try:
            self.mtx_adjustment = files.read_csv_file(".add")
        except (NameError, KeyError):
            self.mtx_adjustment = None
        try:
            cardata = files.read_csv_file(".car")
            self["parking_norm"] = cardata["prknorm"]
        except (NameError, KeyError):
            self._values["parking_norm"] = None
        car_cost = files.read_csv_file(".cco", squeeze=False)
        self.car_dist_cost = car_cost["dist_cost"].to_dict()
        truckdata = files.read_csv_file(".trk", squeeze=True)
        files.zone_numbers = all_zone_numbers[all_zone_numbers.searchsorted(external[0]):]
        files.dtype = numpy.float32
        self.externalgrowth = files.read_csv_file(".ext")
        self.trailers_prohibited = list(map(int, truckdata.loc[0, :]))
        self.garbage_destination = list(map(int, truckdata.loc[1, :].dropna()))
        pop = popdata["population"]
        self["population"] = pop
        self["age_7-17"] = popdata["sh_7-17"] * pop
        self["age_18-29"] = popdata["sh_18-29"] * pop
        self["age_30-49"] = popdata["sh_30-49"] * pop
        self["age_50-64"] = popdata["sh_50-64"] * pop
        self["age_65-99"] = popdata["sh_65"] * pop
        self.share["share_age_7-17"] = popdata["sh_7-17"]
        self.share["share_age_18-29"] = popdata["sh_18-29"]
        self.share["share_age_30-49"] = popdata["sh_30-49"]
        self.share["share_age_50-64"] = popdata["sh_50-64"]
        self.share["share_age_65-99"] = popdata["sh_65"]
        self.share["share_age_7-99"] = popdata["sh_7-17"] + popdata["sh_18-29"] + popdata["sh_30-49"] + popdata["sh_50-64"] + popdata["sh_65"]
        self.share["share_female"] = pandas.Series(
            0.5, self.zone_numbers, dtype=numpy.float32)
        self.share["share_male"] = pandas.Series(
            0.5, self.zone_numbers, dtype=numpy.float32)
        self["age_7-17_female"] = 0.5 * popdata["sh_7-17"] * pop
        self["age_18-29_female"] = 0.5 * popdata["sh_18-29"] * pop
        self["age_30-49_female"] = 0.5 * popdata["sh_30-49"] * pop
        self["age_50-64_female"] = 0.5 * popdata["sh_50-64"] * pop
        self["age_65-99_female"] = 0.5 * popdata["sh_65"] * pop
        self["age_7-17_male"] = 0.5 * popdata["sh_7-17"] * pop
        self["age_18-29_male"] = 0.5 * popdata["sh_18-29"] * pop
        self["age_30-49_male"] = 0.5 * popdata["sh_30-49"] * pop
        self["age_50-64_male"] = 0.5 * popdata["sh_50-64"] * pop
        self["age_65-99_male"] = 0.5 * popdata["sh_65"] * pop
        self["income_0-19"] = incdata["sh_income_0-19"] * pop
        self["income_20-39"] = incdata["sh_income_20-39"] * pop
        self["income_40-59"] = incdata["sh_income_40-59"] * pop
        self["income_60-79"] = incdata["sh_income_60-79"] * pop
        self["income_80-99"] = incdata["sh_income_80-99"] * pop
        self["income_100"] = incdata["sh_income_100"] * pop
        self.nr_zones = len(self.zone_numbers)
        wp = workdata["workplaces"]
        self["workplaces"] = wp
        self["sports_in"] = sport_facilities["sports_in"]
        self["sports_out"] = sport_facilities["sports_out"]
        self["area_education"] = buildings["area_edu"]
        self["area_leisure"] = buildings["area_leis"]
        self["service"] = workdata["sh_serv"] * wp
        self["shop"] = workdata["sh_shop"] * wp
        self["hospitality"] = workdata["sh_hosp"] * wp
        self["recreation"] = workdata["sh_recr"] * wp
        self["park_cost"] = parkdata["avg_park_cost"]
        self["park_time"] = parkdata["avg_park_time"]
        self["comprehensive"] = schooldata["compreh"]
        self["upper_secondary"] = schooldata["upper_sec"]
        self["higher_education"] = schooldata["higher_edu"]
        # Create diagonal matrix with zone area
        self["within_zone"] = numpy.full((self.nr_zones, self.nr_zones), 0.0)
        self["within_zone"][numpy.diag_indices(self.nr_zones)] = 1.0
        # Two-way intrazonal distances from building distances
        self["within_zone_dist"] = self["within_zone"] * buildings["building_dist"].values * 2
        self["within_zone_time"] = self["within_zone_dist"] / (20/60) # 20 km/h
        self["within_zone_cost"] = self["within_zone_dist"] * self.car_dist_cost["car_work"]
        # Unavailability of intrazonal tours
        self["within_zone_inf"] = numpy.full((self.nr_zones, self.nr_zones), 0.0)
        self["within_zone_inf"][numpy.diag_indices(self.nr_zones)] = numpy.inf
        # Create matrix where value is True if origin and destination is in
        # same municipality
        municipalities = self.aggregations.mappings["municipality"].values
        within_municipality = municipalities[:, numpy.newaxis] == municipalities
        self["within_municipality"] = within_municipality
        self["outside_municipality"] = ~within_municipality

    def dummy(self, division_type, name, bounds=slice(None)):
        dummy = self.aggregations.mappings[division_type][bounds] == name
        return dummy

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
        self._values[key] = data

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


class BaseZoneData(ZoneData):
    def __init__(self, data_dir: Path, zone_numbers: Sequence,
                 zone_mapping: Optional[pandas.Series] = None):
        all_zone_numbers = numpy.array(zone_numbers)
        peripheral = param.purpose_areas["peripheral"]
        self.zone_numbers = all_zone_numbers[:all_zone_numbers.searchsorted(
            peripheral[1])]
        municipality_centre_mapping = read_mapping(
            data_dir / "koko_suomi_kunta.zmp")
        if zone_mapping is not None:
            municipality_centre_mapping = municipality_centre_mapping.groupby(
                zone_mapping).agg("first")
        zone_indices = pandas.Series(
            range(len(self.zone_numbers)), index=self.zone_numbers)
        files = FileReader(
            data_dir, self.zone_numbers, zone_mapping=zone_mapping)
        aggregations = ZoneAggregations(
            files.read_csv_file(".agg"),
            municipality_centre_mapping.map(zone_indices))
        ZoneData.__init__(
            self, data_dir, zone_numbers, aggregations, zone_mapping)
        files = FileReader(
            data_dir, self.zone_numbers, numpy.float32, zone_mapping)
        self["car_density"] = files.read_csv_file(".car")["car_dens"]
        self["cars_per_1000"] = 1000 * self["car_density"]


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
