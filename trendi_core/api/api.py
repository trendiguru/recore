# -*- coding: utf-8 -*-
# global libs
import falcon
import gevent
from gevent.queue import Queue as geventQueue

from bson import json_util
from rq import Queue

from ..models.image_class import TrendiImage
from .constants import ImageStatus
from .tools import route
from .tools.status_and_relevancy import insert_irrelevant_to_mongo, check_relevancy_and_enqueue,\
                                        check_image_status, map_to_client, add_col_or_renew_seg
from ..master_constants import redis_conn

add_results = Queue('add_results', connection=redis_conn)
application = falcon.API()


def stop_stream_when_ready(q, images_in_process, products_collection):
    gevent.joinall(images_in_process)
    q.put(StopIteration)
    irrelevant = []
    extra_processing = []
    for image in images_in_process:
        if image.status == ImageStatus.NOT_RELEVANT:
            irrelevant.append(image)
        elif image.status == ImageStatus.ADD_COLLECTION or image.status == ImageStatus.RENEW_SEGMENTATION:
            extra_processing.append(image)
        else:
            pass

    gevent.spawn(insert_irrelevant_to_mongo, irrelevant)
    gevent.spawn(add_col_or_renew_seg, extra_processing, products_collection)


def process_img(q, image, products_collection):

    if not image.type or image.type == 'data':  # TODO handle data images!!!!
        q.put('{},{}'.format(image.url, image.status))
        return image, ImageStatus.NOT_RELEVANT

    image, enum_status = check_image_status(image, products_collection)

    if enum_status == ImageStatus.NEW:
        image = check_relevancy_and_enqueue(image, products_collection)

    status = map_to_client[image.method][image.status]
    q.put('{},{}'.format(image.url, status))
    return image


class FalconServer:
    def __init__(self):
        pass

    def on_post(self, req, resp):

        method = req.get_param("method") or 'nd'
        pid = req.get_param("pid") or 'default'
        products_collection = route.get_collection_from_ip_and_pid(req.env['REMOTE_ADDR'], pid)

        data = json_util.loads(req.stream.read())
        page_url = data.get("pageUrl", "NO_PAGE")
        image_url_list = data.get("imageList")

        # Catch the case where user provided image url instead of list
        image_url_list = image_url_list if isinstance(image_url_list, list) else [image_url_list]
        images = [TrendiImage(image_url, page_url, method) for image_url in image_url_list]

        resp.content_type = 'text/html'
        resp.set_header('Access-Control-Allow-Origin', "*")

        q = geventQueue()
        q.put(' ' * 1024)
        images_in_process = [gevent.spawn(process_img, q, image, products_collection) for image in images]
        gevent.spawn(stop_stream_when_ready, q, images_in_process)
        resp.stream = q

        resp.status = falcon.HTTP_200


application.add_route('/', FalconServer())



