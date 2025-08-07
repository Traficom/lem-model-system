import numpy
from typing import Dict

import utils.log as log


def divide_matrices(mtx1: numpy.ndarray,
                    mtx2: numpy.ndarray,
                    description: str):
    """Perform array division where division by zero is skipped.

    Log descriptives min, median, max.
    """
    mask = mtx2 != 0
    mtx = mtx1[mask] / mtx2[mask]
    v = [round(numpy.quantile(mtx, q)) for q in [0.00, 0.50, 1.00]]
    log.debug(f"{description} (min, median, max) {v[0]} - {v[1]} - {v[2]}")

def output_od_los(mtx: numpy.ndarray,
                  mapping: Dict[int, int],
                  mtx_type: str,
                  mode: str):
    los = int(mtx[mapping[202], mapping[17278]])
    los = f"{los//60}h {los%60}min" if "time" in mtx_type else los
    log.debug(f"{mtx_type} {mode} Helsinki - Jyvaskyla: {los}")
