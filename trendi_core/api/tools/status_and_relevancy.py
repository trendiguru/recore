# global libs
import datetime
import bson
from rq import push_connection, Queue
import collections

# ours
from ...master_tools import imgUtils
from ... import master_constants
from ..constants import ImageStatus, ImagesCollection, SegmentationMethod
from ...master_constants import db, redis_conn


push_connection(redis_conn)
start_pipeline = Queue('start_pipeline', connection=redis_conn)
start_synced_pipeline = Queue('start_synced_pipeline', connection=redis_conn)
add_results = Queue('add_results', connection=redis_conn)
push_connection(master_constants.redis_conn)
LABEL_ADDRESS = "http://37.58.101.173:8357/neural/label"

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


def check_relevancy_and_enqueue(img, products):
    img.get_img()

    relevance = image_is_relevant(img.small_data_array)

    if relevance.is_relevant:
        image_obj = {'people': [{'person_id': str(bson.ObjectId()), 'face': face.tolist()} for face in relevance.faces],
                     'image_urls': img.url, 'page_url': img.page_url, 'insert_time': datetime.datetime.now()}
        db.iip.insert_one(image_obj)
        if img.segmentation_method == 'pd':
            start_pipeline.enqueue_call(func="", args=(img.page_url, img.url, products, img.segmentation_method),
                                        ttl=2000, result_ttl=2000, timeout=2000)
        else:
            start_synced_pipeline.enqueue_call(func="", args=(img.page_url, img.url, products, 'nd'),
                                               ttl=2000, result_ttl=2000, timeout=2000)
        img.status = True

    else:
        img.status = False

    return img


def insert_irrelevant_to_mongo(final_batch_results):

    for img in final_batch_results:
        if not img.status:
            img.hash_it()
            try:
                img.label_it()
            except:
                pass
            image_obj = {'image_hash': img.hash, 'image_urls': [img.url], 'page_urls': [img.page_url], 'people': [],
                         'relevant': False, 'saved_date': str(datetime.datetime.utcnow()), 'views': 1,
                         'labels': img.label}
            db.irrelevant_images.insert_one(image_obj)
            db.labeled_irrelevant.insert_one(image_obj)


def image_is_relevant(image):
    """
    main engine function of 'doorman'
    :param image: nXmX3 dim ndarray representing the standard resized image in BGR colormap
    :return: namedtuple 'Relevance': has 2 fields:
                                                    1. isRelevant ('True'/'False')
                                                    2. faces list sorted by relevance (empty list if not relevant)
    Thus - the right use of this function is for example:
    - "if image_is_relevant(image).is_relevant:"
    - "for face in image_is_relevant(image).faces:"
    """
    Relevance = collections.namedtuple('Relevance', ['is_relevant', 'faces'])
    faces_dict = imgUtils.find_face_using_dlib(image, 4)

    if not faces_dict['are_faces']:
        return Relevance(False, [])
    else:
        return Relevance(True, faces_dict['faces'])


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

