import numpy

import utils.log as log


def divide_matrices(
        mtx1: numpy.array, mtx2: numpy.array, description: str) -> numpy.array:
    """Perform array division where division by zero returns zero.

    Log descriptives min, median, max.
    """
    mtx = numpy.divide(mtx1, mtx2, out=numpy.zeros_like(mtx1), where=mtx2>0)
    v = [round(numpy.quantile(mtx, q)) for q in [0.00, 0.50, 1.00]]
    log.debug(f"{description} (min, median, max {v[0]} - {v[1]} - {v[2]}")
    return mtx
