from __future__ import annotations
from typing import Any, Dict, List, Sequence, Optional, Union
import numpy # type: ignore
import pandas

import parameters.zone as param
from utils.read_csv_file import FileReader
from utils.zone_interval import ZoneIntervals, zone_interval
import utils.log as log
from datatypes.zone import Zone


class ZoneData:
    """Container for zone data read from input files.

    Parameters
    ----------
    data_dir : str
        Directory where scenario input data files are found
    zone_numbers : list
        Zone numbers to compare with for validation
    zone_mapping_file : str (optional)
        Name of zone mapping file
    """
    def __init__(self, data_dir: str, zone_numbers: Sequence,
                 zone_mapping_file: Optional[str] = None):
        self._values = {}
        self.share = ShareChecker(self)
        all_zone_numbers = numpy.array(zone_numbers)
        self.all_zone_numbers = all_zone_numbers
        peripheral = param.purpose_areas["peripheral"]
        external = param.purpose_areas["external"]
        self.zone_numbers = all_zone_numbers[:all_zone_numbers.searchsorted(
            peripheral[1])]
        Zone.counter = 0
        self.zones = {number: Zone(number) for number in self.zone_numbers}
        files = FileReader(
            data_dir, self.zone_numbers, numpy.float32, zone_mapping_file)
        popdata = files.read_csv_file(".pop")
        workdata = files.read_csv_file(".wrk")
        schooldata = files.read_csv_file(".edu")
        landdata = files.read_csv_file(".lnd")
        parkdata = files.read_csv_file(".prk")
        files = FileReader(data_dir)
        self.transit_zone = files.read_csv_file(".tco")
        try:
            cardata = files.read_csv_file(".car")
            self["parking_norm"] = cardata["prknorm"]
        except (NameError, KeyError):
            self._values["parking_norm"] = None
        car_cost = files.read_csv_file(".cco", squeeze=False)
        self.car_dist_cost = car_cost["dist_cost"][0]
        truckdata = files.read_csv_file(".trk", squeeze=True)
        files.zone_numbers = all_zone_numbers[all_zone_numbers.searchsorted(external[0]):]
        files.dtype = numpy.float32
        self.externalgrowth = files.read_csv_file(".ext")
        self.trailers_prohibited = list(map(int, truckdata.loc[0, :]))
        self.garbage_destination = list(map(int, truckdata.loc[1, :].dropna()))
        pop = popdata["total"]
        self["population"] = pop
        self.share["share_age_7-17"] = popdata["sh_7-17"]
        self.share["share_age_18-29"] = popdata["sh_1829"]
        self.share["share_age_30-49"] = popdata["sh_3049"]
        self.share["share_age_50-64"] = popdata["sh_5064"]
        self.share["share_age_65-99"] = popdata["sh_65-"]
        self.share["share_age_7-99"] = (self["share_age_7-17"]      
                                        + self["share_age_18-29"]
                                        + self["share_age_30-49"]
                                        + self["share_age_50-64"]
                                        + self["share_age_65-99"])
        self.share["share_age_18-99"] = (self["share_age_7-99"]
                                         -self["share_age_7-17"])
        self.share["share_female"] = pandas.Series(0.5, self.zone_numbers)
        self.share["share_male"] = pandas.Series(0.5, self.zone_numbers)
        self.nr_zones = len(self.zone_numbers)
        self["population_density"] = pop / landdata["builtar"]
        wp = workdata["total"]
        self["workplaces"] = wp
        self["service"] = workdata["sh_serv"] * wp
        self["shops"] = workdata["sh_shop"] * wp
        self["logistics"] = workdata["sh_logi"] * wp
        self["industry"] = workdata["sh_indu"] * wp
        self["parking_cost_work"] = parkdata["parcosw"]
        self["parking_cost_errand"] = parkdata["parcose"]
        self["comprehensive_schools"] = schooldata["compreh"]
        self["secondary_schools"] = schooldata["secndry"]
        self["tertiary_education"] = schooldata["tertiary"]
        self["zone_area"] = landdata["builtar"]
        self.share["share_detached_houses"] = landdata["detach"]
        self["perc_detached_houses_sqrt"] = landdata["detach"] ** 0.5
        self["helsinki"] = self.dummy("municipalities", "Helsinki")
        self["cbd"] = self.dummy("areas", "helsinki_cbd")
        self["lauttasaari"] = self.dummy("areas", "lauttasaari")
        self["helsinki_other"] = self.dummy("areas", "helsinki_other")
        self["espoo_vant_kau"] = self.dummy("areas", "espoo_vantaa")
        self["surrounding"] = self.dummy("areas", "surrounding")
        self["shops_cbd"] = self["cbd"] * self["shops"]
        self["shops_elsewhere"] = (1-self["cbd"]) * self["shops"]
        # Create diagonal matrix with zone area
        self["own_zone"] = numpy.full((self.nr_zones, self.nr_zones), False)
        self["own_zone"][numpy.diag_indices(self.nr_zones)] = True
        self["own_zone_area"] = self["own_zone"] * self["zone_area"].values
        self["own_zone_area_sqrt"] = numpy.sqrt(self["own_zone_area"])
        # Create matrix where value is 1 if origin and destination is in
        # same municipality
        within_municipality = pandas.DataFrame(
            False, self.zone_numbers, self.zone_numbers)
        intervals = ZoneIntervals("municipalities")
        for i in intervals:
            within_municipality.loc[intervals[i], intervals[i]] = True
        self["within_municipality"] = within_municipality.values
        self["outside_municipality"] = ~within_municipality.values

    def dummy(self, division_type, name, bounds=slice(None)):
        dummy = pandas.Series(False, self.zone_numbers[bounds])
        dummy.loc[zone_interval(division_type, name)] = True
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

    def get_freight_data(self) -> pandas.DataFrame:
        """Get zone data for freight traffic calculation.
        
        Returns
        -------
        pandas DataFrame
            Zone data for freight traffic calculation
        """
        freight_variables = (
            "population",
            "workplaces",
            "shops",
            "logistics",
            "industry",
        )
        data = {k: self._values[k] for k in freight_variables}
        return pandas.DataFrame(data)

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
    def __init__(self, data_dir: str, zone_numbers: Sequence,
                 zone_mapping_file: Optional[str] = None):
        ZoneData.__init__(self, data_dir, zone_numbers, zone_mapping_file)
        files = FileReader(
            data_dir, self.zone_numbers, numpy.float32, zone_mapping_file)
        self["car_density"] = files.read_csv_file(".car")["cardens"]
        self["cars_per_1000"] = 1000 * self["car_density"]


class ShareChecker:
    def __init__(self, data):
        self.data = data

    def __setitem__(self, key, data):
        if (data > 1.005).any():
            for (i, val) in data.iteritems():
                if val > 1.005:
                    msg = "{} ({}) for zone {} is larger than one".format(
                        key, val, i).capitalize()
                    log.error(msg)
                    raise ValueError(msg)
        self.data[key] = data
