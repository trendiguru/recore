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
        self.page_url = page_url
        self.segmentation_method = method
        self._type = False
        self.data_array = None
        self.small_data_array = None
        self.small_data_mask = None
        self.hash = None
        self.p_hash = None
        self.label = None
        self._status = ImageStatus.IRRELEVANT
        self.valid = True
        self.faces = []
        self.url_sort()

    @property
    def url(self):
        return self._url

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def type(self):
        return self._type

    def get_img(self):
        if self.data_array is None:
            self.data_array = img_utils.url_to_img_array(self.url)
            self.is_valid()
            if not self.valid:
                logging.warning("image is None. url: {url}".format(url=self.url))

    def url_sort(self):
        # Sorts image urls into "data", True (valid) or False (invalid)
        if self.url.endwith("data"):
            self.data_array = self.url[0:-4]  # TODO - insert data correctly
            self._type = 'data'
        else:
            self._type = all(list(urlparse(self.url))[:3])

    def resize_it(self, new_size=600):
        new_size = new_size
        small_img, _ = img_utils.standard_resize(self.data_array, new_size)
        self.small_data_array = small_img

    def hash_it(self):
        if self.small_data_array is not None:
            self.hash = img_utils.hash_image(self.small_data_array)

    def p_hash_it(self):
        if self.small_data_array is not None:
            self.p_hash = img_utils.p_hash_image(self.small_data_array)

    def label_it(self):
        img_or_url = self.small_data_array or self.url
        self.label = img_utils.label_img(img_or_url)

    def mask_it(self):
        if self.small_data_array is not None:
            self.small_data_mask = img_utils.create_mask_for_db(self.small_data_array)

    def is_valid(self):
        image_area = self.data_array.shape[0] * self.data_array.shape[1]
        min_image_area = 400
        if self.data_array is not None and \
                isinstance(self.data_array, np.ndarray) and \
                image_area >= min_image_area:
            self.valid = True
        else:
            self.valid = False

    def is_relevant(self):
        self.get_img()
        self.resize_it()

        image = img_utils.image_is_relevant(self.small_data_array)

        if image.is_relevant:
            self.status = ImageStatus.NEW_RELEVANT
            self.faces = image.faces
        else:
            self.status = ImageStatus.NEW_NOT_RELEVANT

    def check_status(self, products_collection, images_collection=IMAGES_COLLECTION, segmentation_method=None):
        self._status = img_utils.check_image_status(self, products_collection, images_collection, segmentation_method)
