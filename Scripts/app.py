import logging
import os
import numpy
from assignments.test_assignment_model import TestAssignmentModel
import assignments.departure_time as dt

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath('__file__'))
project_dir = os.path.join(script_dir, "..")
matrix_dir = os.path.join(project_dir, "Matrices")
logger.info("Reading Matrices from " + str(matrix_dir))

ass_model = TestAssignmentModel(matrix_dir)
dtm = dt.DepartureTimeModel(ass_model)
# nr_zones = len(ass_model.get_zone_numbers())
car_matrix = numpy.arange(6).reshape(2, 3)
demand = {
    "hw": {
        "car": car_matrix,
        "transit": car_matrix,
        "bike": car_matrix,
    },
    "hs": {
        "car": car_matrix,
    },
    "ho": {
        "car": car_matrix,
    },
    "freight": {
        "trailer_truck": car_matrix,
        "truck": car_matrix,
        "van": car_matrix,
    },
}

logger.info("Adding demand and assigning")

for purpose in demand:
    for mode in demand[purpose]:
        dtm.add_demand(purpose, mode, demand[purpose][mode])
dtm.assign()

logger.info("Done")
