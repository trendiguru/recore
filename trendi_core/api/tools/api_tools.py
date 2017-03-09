# global libs
from rq import Queue
import gevent

# our libs
from ...master_constants import ImageStatus as IS
from ..constants import map_to_client
from ...master_constants import db, redis_conn, IMAGES_COLLECTION

start_pipeline = Queue('start_pipeline', connection=redis_conn)


def continue_processing(images):
    for image in images:
        image_obj = image.dbify
        if image.status == IS.NEW_NOT_RELEVANT:
            db.irrelevant_images.insert_one(image_obj)
        else:
            if image.id is None:
                res = db[IMAGES_COLLECTION].insert_one(image_obj)
                image.id = res.inserted_id

            start_pipeline.enqueue_call(func="", args=image.jsonify, ttl=2000, result_ttl=2000, timeout=2000)


def stop_stream_when_ready(q, images_in_process):
    gevent.joinall(images_in_process)
    q.put(StopIteration)

    images = [g_item.value for g_item in images_in_process
              if g_item.value.status in
              [IS.NEW_RELEVANT, IS.NEW_NOT_RELEVANT, IS.ADD_COLLECTION, IS.RENEW_SEGMENTATION]]

    continue_processing(images)


def process_img(q, image):
    if not image.url_valid:
        q.put('{},{}'.format(image.url, False))
        return image

    status = map_to_client[image.method][image.status]
    q.put('{},{}'.format(image.url, status))
    return image

