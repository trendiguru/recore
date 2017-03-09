# global libs
from streamparse import Spout
import rq

# our libs
from ....master_constants import redis_conn, db


class NewImageSpout(Spout):
    auto_ack = False

    def initialize(self, stormconf, context):
        self.q = rq.Queue('start_pipeline', connection=redis_conn)
        self.db = db

    def next_tuple(self):
        if self.q.count > 0:
            job = self.q.dequeue()
            image = job.args
            self.emit([image], tup_id=image['url'])

    def fail(self, tup_id):  # TODO handle failures!!!
        self.log("Image Failed\n{}".format(tup_id))

