# global libs
import numpy as np
import cv2

# our libs
from .img_utils import url_to_img_array, image_is_valid, p_hash_image, standard_resize
from ..master_constants import db, fingerprint_version
from ..models.image_class import TrendiImage


def insert_new_item_to_db(product, fp_date=None, collection_name="products"):
    collection = db[collection_name]
    image_url = product["image"]["sizes"]["XLarge"]["url"]

    image = TrendiImage(image_url)
    image.get_img()
    if not image.valid:
        return False
    image.resize_it(400)
    image.p_hash()

    p_hash_exists = collection.find_one({'p_hash': image.p_hash})
    if p_hash_exists:
        if p_hash_exists['download_data']['dl_version'] != fp_date:
            collection.update_one({'_id': p_hash_exists['_id']}, {'$set': {'download_data.dl_version': fp_date}})
        return False

    category = product['categories']

    image.mask_it()

    fingerprint = fp(image, category)
    print 'fingerprint done'
    product["fingerprint"] = fingerprint
    product["download_data"]["first_dl"] = fp_date
    product["download_data"]["dl_version"] = fp_date
    product["download_data"]["fp_version"] = fingerprint_version

    print "insert "
    try:
        db[collection].insert_one(product)
        print "successfull"
    except Exception as error:
        print "failed with {}".format(error)
        return False

    return True


# TODO
def fp(image, mask, category):
    if category in constants.features_per_category:
        fp_features = constants.features_per_category[category]
    else:
        fp_features = constants.features_per_category['other']
    fingerprint = {feature: Greenlet.spawn(get_feature_fp, feature, image, mask) for feature in fp_features}
    gevent.joinall(fingerprint.values())
    fingerprint = {k: v.value for k, v in fingerprint.iteritems()}
    # fingerprint = {feature: get_feature_fp(image, mask, feature) for feature in fp_features}
    return fingerprint


# TODO
def get_feature_fp(feature, image, mask=None):
    if feature == 'color':
        print 'color'
        return color.execute(image, histograms_length, fingerprint_length, mask)
    img = np.copy(image)
    img = resize_keep_aspect(img, output_size=(224,224))
    res = classifier_client.get(feature, img)
    if isinstance(res, dict) and 'data' in res:
        return res['data']
    else:
        return res


# TODO
def histogram(img, bins=histograms_length, fp_length=fingerprint_length, mask=None):
    if mask is None or cv2.countNonZero(mask) == 0:
        mask = np.ones((img.shape[0], img.shape[1]), dtype=np.uint8)
    if mask.shape[0] != img.shape[0] or mask.shape[1] != img.shape[1]:
        print "mask shape: " + str(mask.shape)
        print "image shape: " + str(img.shape)
        raise ValueError('trouble with mask size, resetting to image size')
    n_pixels = cv2.countNonZero(mask)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # OpenCV uses  H: 0 - 180, S: 0 - 255, V: 0 - 255
    # histograms
    hist_hue = cv2.calcHist([hsv], [0], mask, [bins[0]], [0, 180])
    hist_hue = [item for sublist in hist_hue for item in sublist]  # flatten nested
    hist_hue = np.divide(hist_hue, n_pixels)

    hist_sat = cv2.calcHist([hsv], [1], mask, [bins[1]], [0, 255])
    hist_sat = [item for sublist in hist_sat for item in sublist]
    hist_sat = np.divide(hist_sat, n_pixels)

    hist_int = cv2.calcHist([hsv], [2], mask, [bins[2]], [0, 255])
    hist_int = [item for sublist in hist_int for item in sublist]  # flatten nested list
    hist_int = np.divide(hist_int, n_pixels)

    # Uniformity  t(5)=sum(p.^ 2);
    hue_uniformity = np.dot(hist_hue, hist_hue)
    sat_uniformity = np.dot(hist_sat, hist_sat)
    int_uniformity = np.dot(hist_int, hist_int)

    # Entropy   t(6)=-sum(p. *(log2(p+ eps)));
    eps = 1e-15
    max_log_value = np.log2(bins)  # this is same as sum of p log p
    l_hue = -np.log2(hist_hue + eps) / max_log_value[0]
    hue_entropy = np.dot(hist_hue, l_hue)
    l_sat = -np.log2(hist_sat + eps) / max_log_value[1]
    sat_entropy = np.dot(hist_sat, l_sat)
    l_int = -np.log2(hist_int + eps) / max_log_value[2]
    int_entropy = np.dot(hist_int, l_int)

    result_vector = [hue_uniformity, sat_uniformity, int_uniformity, hue_entropy, sat_entropy, int_entropy]
    result_vector = np.concatenate((result_vector, hist_hue, hist_sat, hist_int), axis=0)

    return result_vector[:fp_length]
