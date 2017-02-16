# global libs
from urlparse import urlparse

# ours libs
from ..master_tools import imgUtils

# TODO - add self.img_array
class TrendiImage(object):

    def __init__(self, url, page_url, method):
        self.url = url
        self.page_url = page_url
        self.segmentation_method = method
        self.type = self.url_sort()
        self.small_img_array = None
        self.hash = None
        self.label = None
        self.status = False

    def get_img_by_url(self):
        image = imgUtils.get_cv2_img_array(self.url)
        if image:
            small_img, _ = imgUtils.standard_resize(image, 600)
            self.small_img_array = small_img

    def hash_it(self):
        if self.small_img_array:
            self.img_hash = imgUtils.hash_image(self.small_img_array)

    def label_it(self):
        img_or_url = self.small_img_array or self.url
        self.label = imgUtils.label_img(img_or_url)

    # Sorts image urls into "data", True (valid) or False (invalid)
    def url_sort(self):
        if self.url[:4] == "data":
            return 'data'
        else:
            return all(list(urlparse(self.url))[:3])






