from pathlib import Path
import pandas
import numpy # type: ignore

import utils.log as log


def read_other_data(path: Path, squeeze = False):
    """Read data from space-separated file.

    Parameters
    ----------
    path : Path
        Path to the .tsv file
    squeeze : bool (optional)
        If the parsed data only contains one column and no header

    Returns
    -------
    pandas.DataFrame
    """
    if not path.exists():
        msg = f"Path {path} not found."
        raise NameError(msg)
    header = None if squeeze else "infer"
    data: pandas.DataFrame = pandas.read_csv(
        path, delim_whitespace=True, keep_default_na=False, 
        na_values="", comment='#', header=header)
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
