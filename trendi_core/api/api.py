# -*- coding: utf-8 -*-
# global libs
import falcon
import gevent
from bson import json_util
from rq import Queue

from ..models.image_class import TrendiImage
from .constants import ImageStatus
from .tools import route
from .tools.status_and_relevancy import insert_irrelevant_to_mongo, check_relevancy_and_enqueue,\
                                        check_image_status, map_to_client, add_col_or_renew_seg
from ..master_constants import redis_conn
from ..master_tools import simple_pool

add_results = Queue('add_results', connection=redis_conn)
application = falcon.API()


def respond_when_ready(data, products_collection, method):

    page_url = data.get("pageUrl", "NO_PAGE")
    image_urls = data.get("imageList")
    # Catch the case where user provided image url instead of list
    image_urls = image_urls if isinstance(image_urls, list) else [image_urls]

    # Filter bad urls and split into data/valid groups
    valid_imgs = []
    data_imgs = []   # TODO: handle data imgs
    for image_url in image_urls:
        img = TrendiImage(image_url, page_url, method)
        if img.type == "data":
            data_imgs.append(img)
        elif img.type:
            valid_imgs.append(img)
        else:
            yield bytes('{},{}'.format(img.url, img.status))

    image_status_list = [gevent.spawn(check_image_status, img, products_collection)
                         for img in valid_imgs]
    gevent.joinall(image_status_list)

    imgs_to_rel_check = []
    imgs_needing_extra_work = []
    for gitem in image_status_list:
        img = gitem.value
        if img.status == ImageStatus.NEW:
            imgs_to_rel_check.append(img)
        else:
            if img.status == ImageStatus.ADD_COLLECTION or img.status == ImageStatus.ADD_COLLECTION :
                imgs_needing_extra_work.append(img)
            img.status = map_to_client[img.method][img.status]
            yield bytes('{},{}'.format(img.url, img.status))

    # RELEVANCY CHECK LIOR'S POOLING
    inputs = [(img, products_collection) for img in imgs_to_rel_check]
    final_batch_results = simple_pool.map(check_relevancy_and_enqueue, inputs)
    for img in final_batch_results:
        yield bytes('{},{}'.format(img.url, img.status))

    yield bytes('stop')  # TODO - sync with the frontend demands

    gevent.spawn(insert_irrelevant_to_mongo, final_batch_results)
    gevent.spawn(add_col_or_renew_seg, imgs_needing_extra_work, products_collection)


class FalconServer:
    def __init__(self):
        pass

    def on_post(self, req, resp):
        method = req.get_param("method") or 'nd'
        pid = req.get_param("pid") or 'default'
        products_collection = route.get_collection_from_ip_and_pid(req.env['REMOTE_ADDR'], pid)

        data = json_util.loads(req.stream.read())

        resp.content_type = "application/json"
        resp.set_header('Access-Control-Allow-Origin', "*")
        resp.append_header('transfer-encoding', 'chunked')
        resp.stream = respond_when_ready(data, products_collection, method)
        resp.status = falcon.HTTP_200


application.add_route('/', FalconServer())



