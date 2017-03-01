# global libs
import datetime
from rq import push_connection, Queue

# our libs
from ..constants import ImageStatus, ImagesCollection, SegmentationMethod
from ...master_constants import db, redis_conn


push_connection(redis_conn)
start_pipeline = Queue('start_pipeline', connection=redis_conn)
start_synced_pipeline = Queue('start_synced_pipeline', connection=redis_conn)
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
# ==============================


def check_image_status(image, products_collection, images_collection=ImagesCollection, segmentation_method=None):
    image_obj = db[images_collection].find_one({'image_urls': image.url},
                                               {'people.items.similar_results': 1})
    if image_obj:
        if products_collection in image_obj['people'][0]['items'][0]['similar_results'].keys():
            # TODO: Rethink "method" structure
            if not segmentation_method:
                if has_sufficient_segmentation(image_obj, segmentation_method):
                    image.status = ImageStatus.RENEW_SEGMENTATION
                    return image

            image.status = ImageStatus.READY
            return image
        else:
            image.status = ImageStatus.ADD_COLLECTION
    elif db.iip.find_one({'image_urls': image.url}, {'_id': 1}):
        image.status = ImageStatus.IN_PROGRESS
    elif db.irrelevant_images.find_one({'image_urls': image.url}, {'_id': 1}):
        image.status = ImageStatus.NOT_RELEVANT
    else:
        image.status = ImageStatus.NEW
    return image


def has_sufficient_segmentation(image_obj, segmentation_method=None):
    segmentation_method = segmentation_method or SegmentationMethod
    methods = [person['segmentation_method'] for person in image_obj['people']]
    return all((method == segmentation_method for method in methods))


# TODO: this function needs to be reviewed again
def add_col_or_renew_seg(imgs_list, products_collection):
    for img in imgs_list:
        if img.status == ImageStatus.ADD_COLLECTION:
            # TODO: change add results to be a generic componnent of the pipeline
            add_results.enqueue_call(func=page_results.add_results_from_collection,
                                     args=(image_obj['_id'], products_collection),
                                     ttl=2000, result_ttl=2000, timeout=2000)
        elif img.status == ImageStatus.RENEW_SEGMENTATION:
            image_obj = {'people': [{'person_id': person['_id'], 'face': person['face'],
                                     'gender': person['gender']} for person in image_obj['people']],
                         'image_urls': img.url, 'page_url': img.page_url, 'insert_time': datetime.datetime.now()}
            db.iip.insert_one(image_obj)
            start_pipeline.enqueue_call(func="", args=(img.page_url, img.url, products_collection, 'pd'),
                                        ttl=2000, result_ttl=2000, timeout=2000)
