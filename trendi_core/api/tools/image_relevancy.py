# global libs
import datetime
import bson
from rq import push_connection, Queue
import collections

# ours
from ...master_tools import imgUtils
from ... import master_constants

db = master_constants.db

push_connection(master_constants.redis_conn)
start_pipeline = Queue('start_pipeline', connection=master_constants.redis_conn)
start_synced_pipeline = Queue('start_synced_pipeline', connection=master_constants.redis_conn)
add_results = Queue('add_results', connection=master_constants.redis_conn)
LABEL_ADDRESS = "http://37.58.101.173:8357/neural/label"


def check_and_enqueue(img, products):
    img.get_img_by_url()

    relevance = image_is_relevant(img.small_img_array)

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

