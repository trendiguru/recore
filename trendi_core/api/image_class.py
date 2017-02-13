import hashlib
import requests
from jaweson import msgpack

# ours
from .. import Utils
from .. import background_removal

LABEL_ADDRESS = "http://37.58.101.173:8357/neural/label"


Class img_object(object):
  def __init__(self, url, page_url, method):
    self.url = url
    self.page_url = page_url
    self.segmentation_method = method
    self.type = url_sort(url)
    self.small_img_array = None
    self.img_hash = ''
    self.label = ''

  def get_img_by_url(self):
    image = Utils.get_cv2_img_array(image_url)
    if image is not None:
        small_img, _ = background_removal.standard_resize(image, 600)
        self.small_img_array = small_img
    
  def hash_img(self):
    if self.small_img_array is not None:
      self.img_hash = get_hash(self.small_img_array)
    
  def labelize(self):
    img_or_url = self.small_img_array or self.url
    self.label = labelize(img_or_url)

    

# Sorts image urls into "data", True (valid) or False (invalid)
def url_sort(image_url):
    if image_url[:4] == "data":
        return 'data'
    else:
        return all(list(urlparse(image_url))[:3])

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
