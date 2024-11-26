from pathlib import Path
import parameters.assignment as param
import numpy

def transform_traversal_data(result_path: Path, zones: list):
    """Processes freight model specific traversal files containing
    information on amount of transported tons between gate pair.
    Processed traversal file contents are aggregated as auxiliary matrix.

    Parameters
    ----------
    result_path : Path
        result path where traversal files are located
    zones : list
        zones in network

    Returns
    ----------
    numpy matrix
        Aggregated auxiliary demand of freight modes
    """
    aux_tons = numpy.zeros([len(zones), len(zones)], dtype=numpy.float32)
    for ass_class in param.freight_modes:
        file = result_path / f"{ass_class}.txt"
        aux_tons += read_traversal_file(file, numpy.array(zones))
    return aux_tons

def read_traversal_file(file: Path, zones: numpy.ndarray):
    """Creates assingment class specific traversal file where
    index based cell values are inserted.

    Parameters
    ----------
    file : Path
        path of assignment class specific traversal file
    zones : numpy.ndarray
        zones in network

    Returns
    ----------
    numpy matrix
        ass class specific traversal matrix
    """
    traversal_matrix = numpy.zeros([len(zones), len(zones)], dtype=numpy.float32)
    with open(file) as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            try:
                int(line.split(" ")[0])
            except ValueError:
                continue
            filt_data = list(filter(None, line.split(" ")))
            row_index = numpy.searchsorted(zones, numpy.int32(filt_data[0]))
            col_index = numpy.searchsorted(zones, numpy.int32(filt_data[1]))
            try:
                cell_value = numpy.float32(filt_data[2])
            except ValueError:
                cell_value = parse_cell_value(filt_data[2])
            traversal_matrix[row_index, col_index] += cell_value
    return traversal_matrix

def parse_cell_value(cell: str):
    """Parses engineering notation based auxiliary tons for
    a given matrix cell of a traversal file. Unit mapping is based
    on Emme's engineering notation syntax.

    Parameters
    ----------
    cell : str
        cell as a string to parse

    Returns
    ----------
    float32
        parsed cell value 
    """
    units = {
        "p": 10 ** -12,
        "n": 10 ** -9,
        "u": 10 ** -6,
        "m": 10 ** -3,
        ".": 1,
        "k": 10 ** 3,
        "M": 10 ** 6,
        "G": 10 ** 9,
        "T": 10 ** 12,
    }
    for i, char in enumerate(cell):
        if char not in units.keys():
            continue
        else:
            decimals = f"{cell[:i]}.{cell[i+1:]}"
            value = numpy.float32(decimals) * units[char]
        break
    return value
