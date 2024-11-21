class EmmeMatrix:
    id_counter = 0

    def __init__(self, name, description, scenario_id, default_value=99999):
        id_counter +=1
        self._id = self.id_counter
        self.name = name
        self.description = description
        self.default_value = default_value
        self._scenario_id = scenario_id

    @property
    def id(self):
        return f"mf{self._id}"

    def init(self):
        emmebank = self.emme_project.modeller.emmebank
        if emmebank.matrix(self.id) is not None:
            emmebank.delete_matrix(self.id)
        self.emme_project.create_matrix(
            self.id, self.description, self.description, self.default_value)

    @property
    def data(self):
        return (self.emme_project.modeller.emmebank.matrix(self.id)
               .get_numpy_data(scenario_id=self._scenario_id))

    @property
    def item(self):
        return {self.name: self.data}

    def release(self):
        self.emme_project.modeller.emmebank.delete_matrix(self.id)

    def __add__(self, other):
        return self.data + other

    def __radd__(self, other):
        return other + self.data

    def __mul__(self, other):
        return self.data * other

    def __rmul__(self, other):
        return other * self.data

    def __lt__(self, other):
        return self.data < other

    def __rlt__(self, other):
        return other < self.data

    def __gt__(self, other):
        return self.data > other

    def __rgt__(self, other):
        return other > self.data
