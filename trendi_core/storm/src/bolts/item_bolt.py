# global libs
from streamparse import Bolt

# our libs
from ....master_constants import redis_conn, db


class ProcessItemBolt(Bolt):
    inputs = ['TrendiItem']
    outputs = ['TrendiItem']

    def initialize(self, conf, ctx):
        self.db = db

    def process(self, tup):
        image = tup.values[0]  # TODO TI to json and back
