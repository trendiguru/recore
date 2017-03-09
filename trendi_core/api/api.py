# -*- coding: utf-8 -*-

# global libs
import falcon
import gevent
from gevent.queue import Queue as geventQueue
from bson import json_util

# our libs
from ..models.image_class import TrendiImage
from .tools.api_tools import process_img, stop_stream_when_ready
application = falcon.API()


class FalconServer:
    def __init__(self):
        pass

    def on_post(self, req, resp):

        desired_segmentation = req.get_param("method") or 'nd' # TODO move the method from here!!!
        pid = req.get_param("pid") or 'default'
        addr = req.env['REMOTE_ADDR']

        data = json_util.loads(req.stream.read())
        page_url = data.get("pageUrl", "NO_PAGE")
        image_url_list = data.get("imageList")

        # Catch the case where user provided image url instead of list
        image_url_list = image_url_list if isinstance(image_url_list, list) else [image_url_list]
        images = [TrendiImage(image_url, page_url, desired_segmentation, page_id=pid, addr=addr)
                  for image_url in image_url_list]

        resp.content_type = 'text/html'
        resp.set_header('Access-Control-Allow-Origin', "*")

        q = geventQueue()
        q.put('start!')
        images_in_process = [gevent.spawn(process_img, q, image) for image in images]
        gevent.spawn(stop_stream_when_ready, q, images_in_process)
        resp.stream = q

        resp.status = falcon.HTTP_200


application.add_route('/', FalconServer())



