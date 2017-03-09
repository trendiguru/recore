# global libs
from streamparse import Bolt

# our libs
from ....master_constants import db
from ....models.image_class import TrendiImage


class SplitByPersonBolt(Bolt):

    def initialize(self, conf, ctx):
        pass

    def process(self, tup):
        image = TrendiImage()
        image.jsonify = tup.values[0]
        people = image.split2peoples
        for person in people:
            self.emit([person], stream='person_args')

    def fail(self):  # TODO handle failures!!!
        pass

# TODO
class MergePeopleBolt(Bolt):
    inputs = ['TrendiPerson']

    def initialize(self, conf, ctx):
        self.db = db

    def process(self, tup):
        image = tup.values[0]  # TODO TI to json and back
