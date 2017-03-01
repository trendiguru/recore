# global libs
from urlparse import urlparse
import numpy as np
import logging

# ours libs
from ..master_tools import img_utils
from ..master_constants import ImageStatus, IMAGES_COLLECTION


class TrendiImage(object):

    def __init__(self, url, page_url=None, method=None):
        self._url = url
        self._page_url = page_url
        self._type = False
        self._data_array = None
        self._small_data_array = None
        self._small_data_mask = None
        self._hash = None
        self._p_hash = None
        self._label = None
        self._status = ImageStatus.IRRELEVANT
        self._valid = True
        self._id = None
        self.faces = []
        self.segmentation_method = method
        self.url_sort()

    @property
    def url(self):
        return self._url

    @property
    def page_url(self):
        return self._page_url

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def type(self):
        return self._type

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
        self._hash = img_utils.hash_image(self.small_data_array)
        return self._hash

    @property
    def p_hash(self):
        self._p_hash = img_utils.p_hash_image(self.small_data_array)
        return self._p_hash

    @property
    def label(self):
        img_or_url = self.small_data_array or self.url
        self._label = img_utils.label_img(img_or_url)
        return self._label

    @property
    def mask(self):
        self._small_data_mask = img_utils.create_mask_for_db(self.small_data_array)
        return self._small_data_mask

    @property
    def is_valid(self):
        image_area = self.data_array.shape[0] * self.data_array.shape[1]
        min_image_area = 400
        if self.data_array is not None and \
                isinstance(self.data_array, np.ndarray) and \
                image_area >= min_image_area:
            self._valid = True
        else:
            self._valid = False

        return self._valid

    @property
    def is_relevant(self):
        image = img_utils.image_is_relevant(self.small_data_array)

        if image.is_relevant:
            self.status(ImageStatus.NEW_RELEVANT)
            self.faces = image.faces
        else:
            self.status(ImageStatus.NEW_NOT_RELEVANT)

        return self.status

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    def check_status(self, products_collection, images_collection=IMAGES_COLLECTION, segmentation_method=None):
        status, _id = (img_utils.check_image_status(self, products_collection, images_collection, segmentation_method))
        self.status(status)
        self.id(_id)
        return self.status

    def url_sort(self):
        # Sorts image urls into "data", True (valid) or False (invalid)
        if self.url.startswith("data"):
            self._data_array = self.url[4:]
            self._type = 'data'
        else:
            self._type = all(list(urlparse(self.url))[:3])
