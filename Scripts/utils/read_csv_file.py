from pathlib import Path
from typing import Optional
import pandas
import numpy # type: ignore

import utils.log as log

class FileReader:
    def __init__(self, data_dir: Path, zone_mapping: pandas.Series):
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
        zone_mapping : pandas.Series (optional)
            Mapping between data zones (index) and assignment zones
        """
        self.data_dir = data_dir
        self.mapping = zone_mapping

    def read_zonedata(self, file_name: str, dtype = numpy.float32):
        """Read zone data from space-separated file.

        Parameters
        ----------
        file_name : str

        Returns
        -------
        pandas.DataFrame
        """
        path = self.data_dir / file_name
        if not path.exists():
            msg = f"Path {path} not found."
            raise NameError(msg)
        data: pandas.DataFrame = pandas.read_csv(
            path, delim_whitespace=True, keep_default_na=False, 
            na_values="", comment='#', index_col = "zone_input")
        if data.index.hasnans:
            msg = "Row with only spaces or tabs in file {}".format(path)
            log.error(msg)
            raise IndexError(msg)
        if data.index.has_duplicates:
            raise IndexError("Index in file {} has duplicates".format(path))
        if not data.index.is_monotonic:
            data.sort_index(inplace=True)
            log.warn("File {} is not sorted in ascending order".format(path))
        is_in(data.index, self.mapping.values, file_name, "zone mapping")
        try:
            data = data.astype(dtype=dtype, errors='raise')
        except ValueError:
            msg = f"Zone data {file_name} not convertible to floats."
            log.error(msg)
            raise ValueError(msg)
        # Aggregate
        if "total" in data.columns:
            # If file contains total and shares of total,
            # shares are aggregated as averages with total as weight
            data = data.groupby(self.mapping).agg(avg, weights=data["total"])
        else:
            share_cols = [col for col in data.columns
                if ("sh_" in col or "avg_" in col or "dummy" in col)]
            text_cols = data.columns[data.dtypes == object]
            funcs = dict.fromkeys(data.columns, "sum")
            for col in share_cols:
                funcs[col] = "mean"
            for col in text_cols:
                funcs[col] = "first"
            data = data.groupby(self.mapping).agg(funcs)
        data.index = data.index.astype(int)
        return data
    
    def read_other_data(self, file_name: str, squeeze = False):
        """Read data from space-separated file.

        Parameters
        ----------
        file_name : str
        squeeze : bool (optional)
            If the parsed data only contains one column and no header

        Returns
        -------
        pandas.DataFrame
        """
        path = self.data_dir / file_name
        if not path.exists():
            msg = f"Path {path} not found."
            raise NameError(msg)
        header = None if squeeze else "infer"
        data: pandas.DataFrame = pandas.read_csv(
            path, delim_whitespace=True, keep_default_na=False, 
            na_values="", comment='#', header = header)
        try:
            data = data.set_index("node_label")
        except KeyError:
            pass
        if squeeze:
            data = data.squeeze()
        for i in data.index:
            try:
                if numpy.isnan(i):
                    msg = "Row with only spaces or tabs in file {}".format(path)
                    log.error(msg)
                    raise IndexError(msg)
            except TypeError:
                # Text indices are ok and should not raise an exception
                pass
        return data

def read_mapping(path: Path, zone_numbers: list) -> pandas.Series:
    """Read mapping from space-separated files.

    Parameters
    ----------
    Path : Path
    zone_numbers : list
        Zone numbers to compare with for validation
    """
    data = pandas.read_csv(path, delim_whitespace=True, index_col="zone_input").squeeze()
    is_in(numpy.array(zone_numbers), data.index.values, "assignment zones", path)
    is_in(data.values, numpy.array(zone_numbers), path, "assignment zones")
    return data

def avg(data, weights):
    if data.name == weights.name:
        return sum(data)
    try:
        return numpy.average(data, weights=weights[data.index])
    except ZeroDivisionError:
        return 0

def is_in(array1: numpy.array, array2: numpy.array,
          name1: str, name2: str):
    if array1.size != array2.size or (array1 != array2).any():
        for i in array1:
            if i not in array2:
                msg = f"Zone number {i} from {name1} not found in {name2}"
                log.error(msg)
                raise IndexError(msg)
