# global libs
from streamparse import Bolt

# our libs
from ....master_constants import redis_conn, db
from ....models.person_class import TrendiPerson


class SplitByItemBolt(Bolt):

    def initialize(self, conf, ctx):
        pass

    def process(self, tup):
        person = TrendiPerson()
        person.jsonify = tup.values[0]
        items = person.items
        for item in items:
            self.emit([item], stream='item_args')

    def fail(self):  # TODO handle failures!!!
        pass

# TODO
class MergeItemsBolt(Bolt):
    inputs = ['TrendiItem']
    outputs = ['TrendiPerson']

    def initialize(self, conf, ctx):
        self.db = db

    def process(self, tup):
        image = tup.values[0]  # TODO TI to json and back
