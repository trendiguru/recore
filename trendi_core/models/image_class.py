# global libs
from urlparse import urlparse
import numpy as np
import logging
import datetime
import tldextract

# ours libs
from ..master_tools import img_utils
from ..master_constants import db, ImageStatus as IS, IMAGES_COLLECTION
from ..api.tools import route


class TrendiImage(object):

    def __init__(self, url=None, page_url=None, desired_segmentation=None,
                 desired_collection=None, page_id=None, addr=None):
        self._url = url
        self._page_url = page_url
        self._desired_collection = desired_collection
        self._desired_segmentation = desired_segmentation
        self._page_id = page_id
        self._addr = addr
        self._domain = None
        self._url_valid = False
        self._data_array = None
        self._small_data_array = None
        self._small_data_mask = None
        self._hash = None
        self._p_hash = None
        self._status = None
        self._valid = True
        self._id = None
        self._existing_collections = None
        self._existing_segmentations = None
        self._people = []
        self._date = datetime.datetime.utcnow()
        self._views = 1

    @property
    def url(self):
        return self._url

    @property
    def url_valid(self):
        if self.url.startswith("data"):
            self._data_array = img_utils.data_url_to_cv2_img(self.url)
            self._url_valid = True
        else:
            self._url_valid = all(list(urlparse(self.url))[:3])
        return self._url_valid

    @property
    def page_url(self):
        return self._page_url

    @property
    def status(self):
        if self._status is None:
            self.check_image_status()
            if self.status == IS.NEW_RELEVANT:
                self.is_relevant()
        return self.status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def data_array(self):
        if self._data_array is None:
            self._data_array = img_utils.url_to_img_array(self.url)
            if not self.is_valid:
                    logging.warning("image is None. url: {url}".format(url=self.url))
        return self._data_array

    @property
    def small_data_array(self):
        if self._small_data_array is None:
            self._small_data_array, _ = img_utils.standard_resize(self.data_array, 600)
        return self._small_data_array

    @property
    def hash(self):
        if self._hash is None:
            self._hash = img_utils.hash_image(self.small_data_array)
        return self._hash

    @property
    def p_hash(self):
        if self._p_hash is None:
            self._p_hash = img_utils.p_hash_image(self.small_data_array)
        return self._p_hash

    @property
    def mask(self):
        if self._small_data_mask is None:
            self._small_data_mask = img_utils.create_mask_for_db(self.small_data_array)
        return self._small_data_mask

    @property
    def is_valid(self):
        self._valid = False
        if self.data_array is not None:
            image_area = self.data_array.shape[0] * self.data_array.shape[1]
            min_image_area = 400
            if isinstance(self.data_array, np.ndarray) and image_area >= min_image_area:
                self._valid = True

        return self._valid

    @property
    def is_relevant(self):
        image = img_utils.image_is_relevant(self.small_data_array)

        if image.is_relevant:
            self.status = IS.NEW_RELEVANT
            for face in image.faces:
                people_obj = {'face': face}
                self._people.append(people_obj)
        else:
            self.status(IS.NEW_NOT_RELEVANT)

        return self.status

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def products_collection(self):
        return self._desired_collection

    @property
    def segmentation_method(self):
        return self._desired_segmentation

    @segmentation_method.setter
    def segmentation_method(self, value):
        self._desired_segmentation = value

    @property
    def jsonify(self):
        image_object = {'url': self.url,
                        'page_url': self.page_url,
                        'data_array': self.data_array.tolist(),
                        'small_data_array': self.small_data_array.tolist(),
                        'small_data_mask': self.mask.tolist(),
                        'hash': self.hash,
                        'p_hash': self.p_hash,
                        'status': self.status,
                        'id': self.id,
                        'domain': self.domain,
                        'desired_collection': self.products_collection,
                        'desired_segmentation': self.segmentation_method,
                        'people': self._people}
        return image_object

    @jsonify.setter
    def jsonify(self, image_object):
        self._url = image_object['url']
        self._page_url = image_object['page_url']
        self._data_array = image_object['data_array']
        self._small_data_array = image_object['small_data_array']
        self._small_data_mask = image_object['small_data_mask']
        self._hash = image_object['hash']
        self._p_hash = image_object['p_hash']
        self.status = image_object['status']
        self._id = image_object['id']
        self._desired_collection = image_object['desired_collection']
        self._desired_segmentation = image_object['desired_segmentation']
        self._people = image_object['people']

    @property
    def desired_collection(self):
        if self._desired_collection is None:
            if self._page_id is not None and self._addr is not None:
                self._desired_collection = route.get_collection_from_ip_and_pid(self._addr, self._page_id)
        return self._desired_collection

    @property
    def domain(self):
        if self._domain is None:
            self._domain = tldextract.extract(self.page_url).registered_domain
        return self._domain

    @property
    def people(self):
            return self._people

    @property
    def dbify(self):
        image_object = {'saved_date': self._date,
                        'domain': self.domain,
                        'page_urls': [self.page_url],
                        'image_urls': [self.url],
                        'image_hash': self.hash,
                        'views': self._views,
                        'people': self.people,
                        'collections': self._existing_collections}

        return image_object

    @dbify.setter
    def dbify(self, image_object):
        self._url = image_object['image_urls'][0]
        self._page_url = image_object['page_url']
        self._hash = image_object['hash']
        self._p_hash = image_object['p_hash']
        self._id = image_object['_id']
        self._people = [person for person in image_object['people']]
        self._existing_collections = [col for col in self._people[0]['items'][0]['similar_resiults'].keys()]
        methods = list(set([person['segmentation_method'] for person in self._people]))
        self._existing_segmentations = methods

    def check_image_status(self, images_collection=IMAGES_COLLECTION):
        image_obj = db[images_collection].find_one({'image_urls': self._url},
                                                   {'people.items.similar_results': 1})

        if image_obj is not None:
            self.dbify = image_obj
            if self._desired_segmentation not in self._existing_segmentations:
                self.status = IS.RENEW_SEGMENTATION
            elif self._desired_collection not in self._existing_collections:
                self.status = IS.ADD_COLLECTION
            else:
                self.status = IS.READY

        elif db.irrelevant_images.find_one({'image_urls': self._url}, {'_id': 1}) is not None:
            self.status = IS.NOT_RELEVANT
        else:
            self.status = IS.NEW_RELEVANT

    @property
    def split2peoples(self):
        global_image_fields = {'url': self.url,
                               'page_url': self.page_url,
                               'data_array': self.data_array.tolist(),
                               'small_data_array': self.small_data_array.tolist(),
                               'small_data_mask': self.mask.tolist(),
                               'id': self.id,
                               'domain': self.domain,
                               'desired_collection': self.products_collection,
                               'desired_segmentation': self.segmentation_method}
        people = []
        for person in self.people:
            person.update(global_image_fields)
            people.append(person)

        return people

