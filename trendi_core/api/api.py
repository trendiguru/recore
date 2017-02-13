# -*- coding: utf-8 -*-

from bson import json_util
import gevent
import falcon
from ..tools import simple_pool
import traceback
from urlparse import urlparse
from ..constants import db, redis_conn
from img_class import img_object
import img_relevancy
from rq import Queue

add_results = Queue('add_results', connection=redis_conn)


# ==============================

map_to_client = {"nd":
                     {ImageStatus.NEW: False,
                      ImageStatus.ADD_COLLECTION: False,
                      ImageStatus.RENEW_SEGMENTATION: True,
                      ImageStatus.IN_PROGRESS: True,
                      ImageStatus.READY: True,
                      ImageStatus.NOT_RELEVANT: False},
                 "pd":
                     {ImageStatus.NEW: False,
                      ImageStatus.ADD_COLLECTION: False,
                      ImageStatus.RENEW_SEGMENTATION: True,
                      ImageStatus.IN_PROGRESS: False,
                      ImageStatus.READY: True,
                      ImageStatus.NOT_RELEVANT: False}}


def on_post(self, req, resp):
    ret = {"success": False}

    method = req.get_param("method") or 'nd'
    pid = req.get_param("pid") or 'default'

    products_collection = page_results.get_collection_from_ip_and_pid(req.env['REMOTE_ADDR'], pid)

    data = json_util.loads(req.stream.read())
    page_url = data.get("pageUrl", "NO_PAGE")
    image_urls = data.get("imageList")
    # Catch the case where user provided image url instead of list
    image_urls = image_urls if isinstance(image_urls, list) else [image_urls]
    # Filter bad urls and split into data/valid groups
    valid_urls = []
    data_urls = []
    for image_url in image_urls:
        img = img_object(image_url, page_url, method)
        if img.type == "data":
            data_urls.append(image_url)
        elif img.type:
            valid_urls.append(image_url)

    image_status_dict = {url: gevent.spawn(check_image_status, url, products_collection)
                         for url in valid_urls}
    gevent.joinall(image_status_dict.values())
    image_status_dict = {url: green_status.value for url, green_status in image_status_dict.iteritems()}
    relevancy_dict = {url: map_to_client[method][status]
                      for url, status in image_status_dict.iteritems()}

    urls_to_rel_check = (url for url, status in image_status_dict.iteritems() if status == ImageStatus.NEW)
    # RELEVANCY CHECK LIOR'S POOLING
    inputs = [(image_url, page_url, products_collection, method) for image_url in urls_to_rel_check]
    outs = simple_pool.map(img_relevancy.check__and_enqueue, inputs)
    relevancy_dict.update({images_to_rel_check[i]: outs[i] for i in xrange(len(images_to_rel_check))})

    ret["relevancy_dict"] = relevancy_dict

    resp.data = json_util.dumps(ret)
    resp.content_type = 'application/json'
    resp.status = falcon.HTTP_200

def check_image_status(image_url, images_collection, products_collection, segmentation_method=None):
    image_obj = db[images_collection].find_one({'image_urls': image_url},
                                               {'people.items.similar_results': 1})
    if image_obj:
        if products_collection in image_obj['people'][0]['items'][0]['similar_results'].keys():
            # TODO: Rethink "method" structure
            if has_sufficient_segmentation(image_obj, segmentation_method):
                return ImageStatus.RENEW_SEGMENTATION

            return ImageStatus.READY
        else:
            return ImageStatus.ADD_COLLECTION
    elif db.iip.find_one({'image_urls': image_url}, {'_id': 1}):
        return ImageStatus.IN_PROGRESS
    elif db.irrelevant_images.find_one({'image_urls': image_url}, {'_id': 1}):
        return ImageStatus.NOT_RELEVANT
    else:
        return ImageStatus.NEW


def has_sufficient_segmentation(image_obj, segementation_method=None):
    segementation_method = segementation_method or constants.default_segmentation_method
    methods = [person['segmentation_method'] for person in image_obj['people']]
    return all((method == segementation_method for method in methods))


# Make sure these run in a queue later
for url, status in checked_images:
    if status == ImageStatus.ADD_COLLECTION:
        add_results.enqueue_call(func=page_results.add_results_from_collection,
                                 args=(image_obj['_id'], products_collection),
                                 ttl=2000, result_ttl=2000, timeout=2000)
    elif status == ImageStatus.RENEW_SEGMENTATION:
        image_obj = {'people': [{'person_id': person['_id'], 'face': person['face'],
                                 'gender': person['gender']} for person in image_obj['people']],
                     'image_urls': url, 'page_url': page_url, 'insert_time': datetime.datetime.now()}
        db.iip.insert_one(image_obj)
        start_pipeline.enqueue_call(func="", args=(page_url, url, products_collection, 'pd'),
                                    ttl=2000, result_ttl=2000, timeout=2000)

