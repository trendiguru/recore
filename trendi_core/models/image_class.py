# global libs
from urlparse import urlparse

# ours libs
from ..master_tools import imgUtils


class TrendiImage(object):

    def __init__(self, url, page_url, method):
        self.url = url
        self.page_url = page_url
        self.segmentation_method = method
        self.type = self.url_sort()
        self.data_array = None
        self.small_data_array = None
        self.hash = None
        self.label = None
        self.status = False

    def get_img(self):
        if self.data_array is None:
            self.data_array = imgUtils.url_to_img_array(self.url)

        if self.data_array is not None:
            small_img, _ = imgUtils.standard_resize(self.data_array, 600)
            self.small_data_array = small_img

    def hash_it(self):
        if self.small_data_array:
            self.hash = imgUtils.hash_image(self.small_data_array)

    def label_it(self):
        img_or_url = self.small_data_array or self.url
        self.label = imgUtils.label_img(img_or_url)

    # Sorts image urls into "data", True (valid) or False (invalid)
    def url_sort(self):
        if self.url[:4] == "data":
            self.data_array = self.url[0:-4]  # TODO - insert data correctly
            return 'data'
        else:
            return all(list(urlparse(self.url))[:3])




