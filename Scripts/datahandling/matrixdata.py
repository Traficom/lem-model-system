from __future__ import annotations
import os
from typing import TYPE_CHECKING, Optional
import openmatrix as omx # type: ignore
import numpy # type: ignore
import pandas
from contextlib import contextmanager
if TYPE_CHECKING:
    from datahandling.zonedata import BaseZoneData

import utils.log as log
import parameters.assignment as param
import parameters.zone as zone_param


class MatrixData:
    def __init__(self, path: str):
        self.path = path
        if not os.path.exists(self.path):
            os.makedirs(self.path)
    
    @contextmanager
    def open(self, 
             mtx_type: str, 
             time_period: str, 
             zone_numbers: Optional[numpy.ndarray] = None, 
             m: str = 'r'):
        file_name = os.path.join(self.path, mtx_type+'_'+time_period+".omx")
        mtxfile = MatrixFile(omx.open_file(file_name, m), zone_numbers)
        yield mtxfile
        mtxfile.close()


class MatrixFile:
    def __init__(self, omx_file: omx.File, zone_numbers: numpy.ndarray):
        self._file = omx_file
        self.missing_zones = []
        if zone_numbers is None:
            pass
        elif omx_file.mode == 'r':
            path = omx_file.filename
            mtx_numbers = self.zone_numbers
            if (numpy.diff(mtx_numbers) <= 0).any():
                msg = "Zone numbers not in strictly ascending order in file {}".format(
                    path)
                log.error(msg)
                raise IndexError(msg)
            if mtx_numbers != zone_numbers:
                for i in mtx_numbers:
                    if i not in zone_numbers:
                        msg = "Zone number {} from file {} not found in network".format(
                            i, path)
                        log.error(msg)
                        raise IndexError(msg)
                for i in zone_numbers:
                    if i not in mtx_numbers:
                        self.missing_zones.append(i)
                log.warn("Zone number(s) {} missing from file {}{}".format(
                             self.missing_zones, path,
                             ", adding zero row(s) and column(s)"))
                self.new_zone_numbers = zone_numbers
            ass_classes = self.matrix_list
            transport_classes = (("truck", "trailer_truck") 
                                 if "freight" in path
                                 else param.transport_classes)
            for ass_class in transport_classes:
                if ass_class not in ass_classes:
                    msg = "File {} does not contain {} matrix.".format(
                        path, ass_class)
                    log.error(msg)
                    raise IndexError(msg)
        else:
            self.mapping = zone_numbers
    
    def close(self):
        self._file.close()
    
    def __getitem__(self, mode: str):
        mtx = numpy.array(self._file[mode])
        nr_zones = len(self.zone_numbers)
        dim = (nr_zones, nr_zones)
        if mtx.shape != dim:
            msg = "Matrix {} in file {} has dimensions {}, should be {}".format(
                mode, self._file.filename, mtx.shape, dim)
            log.error(msg)
            raise IndexError(msg)
        if numpy.isnan(mtx).any():
            msg = "Matrix {} in file {} contains NA values".format(
                mode, self._file.filename)
            log.error(msg)
            raise ValueError(msg)
        if (mtx < 0).any():
            msg = "Matrix {} in file {} contains negative values".format(
                mode, self._file.filename)
            log.error(msg)
            raise ValueError(msg)
        if self.missing_zones:
            mtx = pandas.DataFrame(mtx, self.zone_numbers, self.zone_numbers)
            mtx = mtx.reindex(
                index=self.new_zone_numbers, columns=self.new_zone_numbers,
                fill_value=0)
            mtx = mtx.values
        return mtx

    def __setitem__(self, mode, data):
        self._file[mode] = data

    @property
    def zone_numbers(self):
        return self._file.mapentries("zone_number")

    @property
    def mapping(self):
        return self._file.mapping("zone_number")

    @mapping.setter
    def mapping(self, zone_numbers):
        self._file.create_mapping("zone_number", zone_numbers)

    @property
    def matrix_list(self):
        return self._file.list_matrices()
