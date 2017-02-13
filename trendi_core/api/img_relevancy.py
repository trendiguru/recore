import hashlib
import requests
import datetime
import bson
from jaweson import msgpack
from rq import push_connection, Queue

# ours
from .. import Utils
from .. import constants
from .. import background_removal
from .. import page_results
db = constants.db

push_connection(constants.redis_conn)
start_pipeline = Queue('start_pipeline', connection=constants.redis_conn)
start_synced_pipeline = Queue('start_synced_pipeline', connection=constants.redis_conn)
add_results = Queue('add_results', connection=constants.redis_conn)
LABEL_ADDRESS = "http://37.58.101.173:8357/neural/label"


def check_and_enqueue(image_url, page_url, products, method):
    image = Utils.get_cv2_img_array(image_url)
    if image is None:
        return False
        
    small_img, rr = background_removal.standard_resize(image, 600)
    relevance = background_removal.image_is_relevant(small_img, use_caffe=False, image_url=image_url)

    if relevance.is_relevant:
        image_obj = {'people': [{'person_id': str(bson.ObjectId()), 'face': face.tolist()} for face in relevance.faces],
                     'image_urls': image_url, 'page_url': page_url, 'insert_time': datetime.datetime.now()}
        db.iip.insert_one(image_obj)
        if method == 'pd':
            start_pipeline.enqueue_call(func="", args=(page_url, image_url, products, method),
                                        ttl=2000, result_ttl=2000, timeout=2000)
        else:
            start_synced_pipeline.enqueue_call(func="", args=(page_url, image_url, products, 'nd'),
                                               ttl=2000, result_ttl=2000, timeout=2000)
        return True
    else:
        # use gevent to parralelize
        if method != 'pd':
            return False
            
        hashed = get_hash(image)
        try:
            label = labelize(image).replace('.', '')
        except:
            label = None
        image_obj = {'image_hash': hashed, 'image_urls': [image_url], 'page_urls': [page_url], 'people': [],
                     'relevant': False, 'saved_date': str(datetime.datetime.utcnow()), 'views': 1,
                     'labels': label}
        db.irrelevant_images.insert_one(image_obj)
        db.labeled_irrelevant.insert_one(image_obj)
        return image_obj


def labelize(image_or_url):
    try:
        data = msgpack.dumps({"image": image_or_url})
        resp = requests.post(LABEL_ADDRESS, data)
        labels = msgpack.loads(resp.content)["labels"]
        return {key: float(val) for key, val in labels.items()}
    except:
        return []


def get_hash(image):
    m = hashlib.md5()
    m.update(image)
    url_hash = m.hexdigest()
    return url_hash
