# global libs
from urlparse import urlparse
import numpy as np
import logging

# ours libs
from ..master_tools import img_utils
from ..master_constants import ImageStatus, IMAGES_COLLECTION


class TrendiPerson(object):

    def __init__(self):
        self._url = None
        self._page_url = None
        self._id = None
        self._domain = None
        self._full_data_array = None
        self._isolated_person_array = None
        self._mask = None
        self._desired_collection = None
        self._desired_segmentation = None
        self._valid = False
        self._person_bb = None
        self._face = None

    @property
    def url(self):
        return self._url

    @property
    def page_url(self):
        return self._page_url

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
    def is_valid(self):
        if self.data_array is not None:
            image_area = self.data_array.shape[0] * self.data_array.shape[1]
            min_image_area = 400
            if isinstance(self.data_array, np.ndarray) and image_area >= min_image_area:
                self._valid = True

        return self._valid

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
    def mask(self):
        if self._mask is None:
            self._mask = img_utils.create_mask_for_db(self.small_data_array)
        return self._mask

    @property
    def domain(self):
        return self._domain

    @property
    def bb(self):
        return self._person_bb

    @property
    def face(self):
        return self._face

    @property
    def jsonify(self):
        person_object = {'url': self.url,
                         'page_url': self.page_url,
                         'id': self.id,
                         'domain': self.domain,
                         'full_data_array': self.data_array,
                         'isolated_person_array': self.small_data_array,
                         'mask': self.mask,
                         'desired_collection': self.products_collection,
                         'desired_segmentation': self.segmentation_method,
                         'person_bb': self.bb,
                         'face': self.face}
        return person_object

    @jsonify.setter
    def jsonify(self, person_object):
        self._url = person_object['url']
        self._page_url = person_object['page_url']
        self._full_data_array = person_object['data_array']
        self._small_data_array = person_object['small_data_array']
        self._mask = person_object['small_data_mask']
        self._id = person_object['id']
        self._desired_collection = person_object['desired_collection']
        self._desired_segmentation = person_object['desired_segmentation']


    isolated_image = background_removal.person_isolation(image, face)

    person_bb = Utils.get_person_bb_from_face(face, image.shape)
