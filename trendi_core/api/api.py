# -*- coding: utf-8 -*-

# global libs
import falcon
import gevent
from gevent.queue import Queue as geventQueue
from bson import json_util
from ..models.image_class import TrendiImage
from ..master_constants import ImageStatus as IS
from .tools import route
from .tools.extra_processing import continue_processing
from .constants import map_to_client


application = falcon.API()


def stop_stream_when_ready(q, images_in_process, products_collection):

    gevent.joinall(images_in_process)
    q.put(StopIteration)

    images = [g_item.value for g_item in images_in_process
              if g_item.value.status in
              [IS.NEW_RELEVANT, IS.NEW_NOT_RELEVANT, IS.ADD_COLLECTION, IS.RENEW_SEGMENTATION]]

    continue_processing(images, products_collection)


def process_img(q, image, products_collection):

    if not image.type or image.type == 'data':  # TODO handle data images!!!!
        q.put('{},{}'.format(image.url, False))
        return image

    image.check_status(image, products_collection)

    if image.status == IS.NEW_RELEVANT:
        image.is_relevant()

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
        q.put('start!')
        images_in_process = [gevent.spawn(process_img, q, image, products_collection) for image in images]
        gevent.spawn(stop_stream_when_ready, q, images_in_process, products_collection)
        resp.stream = q

        resp.status = falcon.HTTP_200


application.add_route('/', FalconServer())



