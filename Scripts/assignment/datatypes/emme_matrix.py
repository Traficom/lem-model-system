import numpy

import utils.log as log


class EmmeMatrix:
    id_counter = 0

    def __init__(self, name, description, emme_project, scenario_id, default_value=99999):
        EmmeMatrix.id_counter +=1
        self._id = EmmeMatrix.id_counter
        self.name = name
        self.description = description
        self.default_value = default_value
        self._emme_project = emme_project
        self._scenario_id = scenario_id

    @property
    def id(self):
        return f"mf{self._id}"

    def init(self):
        emmebank = self._emme_project.modeller.emmebank
        if emmebank.matrix(self.id) is not None:
            emmebank.delete_matrix(self.id)
        self._emme_project.create_matrix(
            self.id, self.description, self.description, self.default_value)

    def set(self, matrix):
        if numpy.isnan(matrix).any():
            msg = ("NAs in demand matrix "
                   + "would cause infinite loop in Emme assignment.")
            log.error(msg)
            raise ValueError(msg)
        else:
            (self._emme_project.modeller.emmebank.matrix(self.id)
             .set_numpy_data(matrix, scenario_id=self._scenario_id))

    @property
    def data(self):
        return (self._emme_project.modeller.emmebank.matrix(self.id)
               .get_numpy_data(scenario_id=self._scenario_id))

    @property
    def item(self):
        return {self.name: self.data}

    def release(self):
        self._emme_project.modeller.emmebank.delete_matrix(self.id)


class PermanentEmmeMatrix(EmmeMatrix):
    def __init__(self, *args, **kwargs):
        EmmeMatrix.__init__(self, *args, **kwargs)
        EmmeMatrix.init(self)

    def init(self):
        pass

    def release(self):
        pass
