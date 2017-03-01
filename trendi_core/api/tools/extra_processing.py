# global libs
import datetime
import bson
from rq import push_connection, Queue

# ours
from ... import master_constants
from ...master_constants import db, redis_conn, ImageStatus


push_connection(redis_conn)
start_pipeline = Queue('start_pipeline', connection=redis_conn)
start_synced_pipeline = Queue('start_synced_pipeline', connection=redis_conn)
add_results = Queue('add_results', connection=redis_conn)
push_connection(master_constants.redis_conn)
LABEL_ADDRESS = "http://37.58.101.173:8357/neural/label"


# TODO: this function needs to be reviewed again
def continue_processing(images, products_collection):

    for image in images:

        if image.status == ImageStatus.ADD_COLLECTION:
            # TODO: change add results to be a generic componnent of the pipeline
            add_results.enqueue_call(func=page_results.add_results_from_collection,
                                     args=(image_obj['_id'], products_collection),
                                     ttl=2000, result_ttl=2000, timeout=2000)

        elif image.status == ImageStatus.RENEW_SEGMENTATION:
            image_obj = {'people': [{'person_id': person['_id'], 'face': person['face'],
                                     'gender': person['gender']} for person in image_obj['people']],
                         'image_urls': image.url, 'page_url': image.page_url, 'insert_time': datetime.datetime.now()}
            db.iip.insert_one(image_obj)
            start_pipeline.enqueue_call(func="", args=(image.page_url, image.url, products_collection, 'pd'),
                                        ttl=2000, result_ttl=2000, timeout=2000)

        else:

            image.hash_it()
            try:
                image.label_it()
            except:
                pass

            image_obj = {'image_hash': image.hash, 'image_urls': [image.url], 'page_urls': [image.page_url], 'people': [],
                         'relevant': False, 'saved_date': str(datetime.datetime.utcnow()), 'views': 1,
                         'insert_time': datetime.datetime.now(),
                         'labels': image.label}

            if image.status == ImageStatus.NEW_RELEVENT:
                image_obj['people'] = \
                    [{'person_id': str(bson.ObjectId()), 'face': face.tolist()} for face in image.faces]

                db.iip.insert_one(image_obj)

                if image.segmentation_method == 'pd':
                    start_pipeline.enqueue_call(func="", args=(image.page_url, image.url,
                                                               products_collection, image.segmentation_method),
                                                ttl=2000, result_ttl=2000, timeout=2000)
                else:
                    start_synced_pipeline.enqueue_call(func="", args=(image.page_url, image.url,
                                                                      products_collection, 'nd'),
                                                       ttl=2000, result_ttl=2000, timeout=2000)

            else:
                db.irrelevant_images.insert_one(image_obj)
                db.labeled_irrelevant.insert_one(image_obj)
