from decimal import DivisionByZero
from itertools import groupby
import os
from typing import Optional
import pandas
import numpy # type: ignore

import utils.log as log

class FileReader:
    def __init__(self, data_dir: str,
                 zone_numbers: Optional[numpy.ndarray] = None,
                 dtype: Optional[numpy.dtype] = None,
                 zone_mapping_file: Optional[str] = None):
        """Read (zone) data from space-separated files.

        If a zone mapping file is provided, data in files
        is aggregated and assigned to new zone numbers according
        to the mapping.

        Parameters
        ----------
        data_dir : str
            Directory where scenario input data files are found
        file_end : str
            Ending of the file in question (e.g., ".pop")
        zone_numbers : ndarray (optional)
            Zone numbers to compare with for validation
        dtype : data type (optional)
            Data type to cast data to
        zone_mapping_file : str (optional)
            Name of zone mapping file
        """
        self.data_dir = data_dir
        self.zone_numbers = zone_numbers
        self.dtype = dtype
        self.map_path = (os.path.join(data_dir, zone_mapping_file)
                             if zone_mapping_file is not None else None)

    def read_csv_file(self, file_end: str, squeeze: bool = False):
        """Read (zone) data from space-separated file.

        Parameters
        ----------
        file_end : str
            Ending of the file in question (e.g., ".pop")
        squeeze : bool (optional)
            If the parsed data only contains one column and no header

        Returns
        -------
        pandas DataFrame
        """
        data_dir = self.data_dir
        zone_numbers = self.zone_numbers
        file_found = False
        for file_name in os.listdir(data_dir):
            if file_name.endswith(file_end):
                if file_found:
                    msg = "Multiple {} files found in folder {}".format(
                        file_end, data_dir)
                    log.error(msg)
                    raise NameError(msg)
                else:
                    path = os.path.join(data_dir, file_name)
                    file_found = True
        if not file_found:
            msg = "No {} file found in folder {}".format(file_end, data_dir)
            # This error should not be logged, as it is sometimes excepted
            raise NameError(msg)
        header = None if squeeze else "infer"
        data: pandas.DataFrame = pandas.read_csv(
            path, delim_whitespace=True, keep_default_na=False,
            na_values="", comment='#', header=header)
        for index_column in ["data_id", "zone_id", "node_label"]:
            if index_column in data.columns:
                data = data.set_index(index_column)
                break
        if squeeze:
            data = data.squeeze()
        if data.index.is_numeric() and data.index.hasnans:
            msg = "Row with only spaces or tabs in file {}".format(path)
            log.error(msg)
            raise IndexError(msg)
        else:
            for i in data.index:
                try:
                    if numpy.isnan(i):
                        msg = "Row with only spaces or tabs in file {}".format(path)
                        log.error(msg)
                        raise IndexError(msg)
                except TypeError:
                    # Text indices are ok and should not raise an exception
                    pass
        if data.index.has_duplicates:
            raise IndexError("Index in file {} has duplicates".format(path))
        if zone_numbers is not None:
            if not data.index.is_monotonic:
                data.sort_index(inplace=True)
                log.warn("File {} is not sorted in ascending order".format(path))
            map_path = self.map_path
            if map_path is not None:
                log_path = map_path
                mapping = pandas.read_csv(map_path, delim_whitespace=True).squeeze()
                mapping = mapping.set_index("data_id")
                if "total" in data.columns:
                    # If file contains total and shares of total,
                    # shares are aggregated as averages with total as weight
                    data = data.groupby(mapping.zone_id).agg(avg, weights=data["total"])
                else:
                    share_cols = [col for col in data.columns
                        if ("sh_" in col or "avg_" in col or "dummy" in col)]
                    text_cols = data.columns[data.dtypes == object]
                    funcs = dict.fromkeys(data.columns, "sum")
                    for col in share_cols:
                        funcs[col] = "mean"
                    for col in text_cols:
                        funcs[col] = "first"
                    data = data.groupby(mapping.zone_id).agg(funcs)
                data.index = data.index.astype(int)
            else:
                log_path = path
            if data.index.size != zone_numbers.size or (data.index != zone_numbers).any():
                for i in data.index:
                    if int(i) not in zone_numbers:
                        msg = "Zone number {} from file {} not found in network".format(
                            i, log_path)
                        log.error(msg)
                        raise IndexError(msg)
                for i in zone_numbers:
                    if i not in data.index:
                        if log_path == map_path and i in mapping.array:
                            # If mapping is ok, then error must be in data file
                            log_path = path
                            i = mapping[mapping == i].index[0]
                        msg = "Zone number {} not found in file {}".format(i, log_path)
                        log.error(msg)
                        raise IndexError(msg)
                msg = "Zone numbers did not match for file {}".format(log_path)
                log.error(msg)
                raise IndexError(msg)
        if self.dtype is not None:
            try:
                data = data.astype(dtype=self.dtype, errors='raise')
            except ValueError:
                msg = "Zone data file {} has values not convertible to floats.".format(
                    file_end)
                log.error(msg)
                raise ValueError(msg)
        return data

def avg (data, weights):
    if data.name == weights.name:
        return sum(data)
    try:
        return numpy.average(data, weights=weights[data.index])
    except ZeroDivisionError:
        return 0
