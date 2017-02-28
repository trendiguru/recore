# global libs
from urlparse import urlparse
import numpy as np
import logging

# ours libs
from ..master_tools import img_utils
from ..master_constants import ImageStatus


class TrendiImage(object):

    def __init__(self, url, page_url=None, method=None):
        self.url = url
        self.page_url = page_url
        self.segmentation_method = method
        self.type = self.url_sort()
        self._data_array = None
        self.small_data_array = None
        self.small_data_mask = None
        self.hash = None
        self.p_hash = None
        self.label = None
        self.status = ImageStatus.NOT_RELEVANT
        self._is_valid = True

    @property
    def data_array(self):
        if self._data_array is None:
            self._data_array = img_utils.url_to_img_array(self.url)
            self.validate_it()
            if not self.valid:
                logging.warning("image is None. url: {url}".format(url=self.url))
        return self._data_array

    def url_sort(self):
        # Sorts image urls into "data", True (valid) or False (invalid)
        if self.url.endwith("data"):
            self.data_array = self.url[0:-4]  # TODO - insert data correctly
            return 'data'
        else:
            return all(list(urlparse(self.url))[:3])

    def resize_it(self, new_size):
        new_size = new_size or 600
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

    @property
    def is_valid(self):
        min_image_area = 400 #TODO: consider moving this
        if isinstance(self.data_array, np.ndarray):
            image_area = self.data_array.shape[0] * self.data_array.shape[1]
            self._is_valid = image_area >= min_image_area:
        return self._is_valid
