# -*- coding: utf-8 -*-
# global libs
import falcon
import gevent
from bson import json_util
from rq import Queue

from tools import route
from trendi_core.api.tools import img_relevancy
from trendi_core.api.tools.image_class import ImgObject
from .constants import ImageStatus, ImagesCollection, SegmentationMethod
from ..master_constants import db, redis_conn
from ..master_tools import simple_pool

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

    products_collection = route.get_collection_from_ip_and_pid(req.env['REMOTE_ADDR'], pid)

    data = json_util.loads(req.stream.read())
    page_url = data.get("pageUrl", "NO_PAGE")
    image_urls = data.get("imageList")
    # Catch the case where user provided image url instead of list
    image_urls = image_urls if isinstance(image_urls, list) else [image_urls]

    # Filter bad urls and split into data/valid groups
    valid_imgs = []
    data_imgs = []  # TODO: handle data imgs
    for image_url in image_urls:
        img = ImgObject(image_url, page_url, method)
        if img.type == "data":
            data_imgs.append(img)
        elif img.type:
            valid_imgs.append(img)

    image_status_list = [gevent.spawn(check_image_status, img, products_collection)
                         for img in valid_imgs]

    gevent.joinall(image_status_list)
    image_status_list = [(item[0], item[1].value) for item in image_status_list]
    relevancy_dict = {img.url: map_to_client[method][status] for img, status in image_status_list}

    imgs_to_rel_check = (img for img, status in image_status_list if status == ImageStatus.NEW)
    # RELEVANCY CHECK LIOR'S POOLING
    inputs = [(img, products_collection) for img in imgs_to_rel_check]
    outs = simple_pool.map(img_relevancy.check_and_enqueue, inputs)
    relevancy_dict.update({imgs_to_rel_check[i].url: outs[i] for i,_ in enumerate(imgs_to_rel_check)})

    ret["relevancy_dict"] = relevancy_dict

    resp.data = json_util.dumps(ret)
    resp.content_type = 'application/json'
    resp.status = falcon.HTTP_200


def check_image_status(image, products_collection,images_collection=ImagesCollection, segmentation_method=None):
    image_obj = db[images_collection].find_one({'image_urls': image.url},
                                               {'people.items.similar_results': 1})
    if image_obj:
        if products_collection in image_obj['people'][0]['items'][0]['similar_results'].keys():
            # TODO: Rethink "method" structure
            if not segmentation_method:
                if has_sufficient_segmentation(image_obj, segmentation_method):
                    return ImageStatus.RENEW_SEGMENTATION

            return image, ImageStatus.READY
        else:
            return image, ImageStatus.ADD_COLLECTION
    elif db.iip.find_one({'image_urls': image.url}, {'_id': 1}):
        return image, ImageStatus.IN_PROGRESS
    elif db.irrelevant_images.find_one({'image_urls': image.url}, {'_id': 1}):
        return image, ImageStatus.NOT_RELEVANT
    else:
        return image, ImageStatus.NEW


def has_sufficient_segmentation(image_obj, segmentation_method=None):
    segmentation_method = segmentation_method or SegmentationMethod
    methods = [person['segmentation_method'] for person in image_obj['people']]
    return all((method == segmentation_method for method in methods))


# TODO -------------IMPORTANT!!!-------------------
# # Make sure these run in a queue later
# for url, sts in checked_images:
#     if sts == ImageStatus.ADD_COLLECTION:
#         add_results.enqueue_call(func=page_results.add_results_from_collection,
#                                  args=(image_obj['_id'], products_collection),
#                                  ttl=2000, result_ttl=2000, timeout=2000)
#     elif sts == ImageStatus.RENEW_SEGMENTATION:
#         image_obj = {'people': [{'person_id': person['_id'], 'face': person['face'],
#                                  'gender': person['gender']} for person in image_obj['people']],
#                      'image_urls': url, 'page_url': page_url, 'insert_time': datetime.datetime.now()}
#         db.iip.insert_one(image_obj)
#         start_pipeline.enqueue_call(func="", args=(page_url, url, products_collection, 'pd'),
#                                     ttl=2000, result_ttl=2000, timeout=2000)

