from __future__ import print_function

# global libs
import requests
from cv2 import imdecode, imwrite
import logging
import numpy as np
import cv2
import dlib
import hashlib
from functools import partial
from jaweson import msgpack
import Image
from scipy import fftpack
import collections

# out libs
from ..master_constants import db, ImageStatus, IMAGES_COLLECTION

detector = dlib.get_frontal_face_detector()
logging.basicConfig(level=logging.WARNING)
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'
LABEL_ADDRESS = "http://37.58.101.173:8357/neural/label"


def label_img(image_or_url):
    try:
        data = msgpack.dumps({"image": image_or_url})
        resp = requests.post(LABEL_ADDRESS, data)
        labels = msgpack.loads(resp.content)["labels"]
        return {key: float(val) for key, val in labels.items()}
    except:
        return None


def url_to_img_array(url):
    if not isinstance(url, basestring):
        logging.warning("input is neither an ndarray nor a string, so I don't know what to do")
        return None

    # replace_https_with_http:
    if 'http' in url and 'https' not in url:
        url = url.replace("https", "http")
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers)
        img_array = imdecode(np.asarray(bytearray(response.content)), 1)
    except requests.ConnectionError:
        logging.warning("connection error - check url or connection")
        return None
    except:
        logging.warning(" error other than connection error - check something other than connection")
        return None

    return img_array


def path_to_img_array(img_path):
    if not isinstance(img_path, basestring):
        logging.warning("bad input - path string is expected")
        return None

    try:
        img_array = cv2.imread(img_path)
    except:
        logging.warning("could not read locally, returning None")
        return None

    return img_array


def download_img_array(img_array, savename):
    if any(savename.endswith(x) for x in ['.jpg', '.jpeg', '.bmp', '.tiff']):
        pass
    else:  # there's no 'normal' filename ending so add .jpg
        savename += '.jpg'

    try:
        imwrite(savename, img_array)
    except:  # this is prob unneeded given the 'else' above
        print('unexpected error in Utils calling imwrite')
        return False

    return True


def download_img_url(img_url, savename):
    img_array = url_to_img_array(img_url)
    if img_array is None:
        return False
    else:
        return download_img_array(img_array, savename)


def standard_resize(image, max_side):
    if image is None:
        return None, 1

    original_h, original_w, _ = image.shape
    if all(side < max_side for side in [original_h, original_w]):
        return image, 1
    aspect_ratio = float(np.amax((original_w, original_h))/float(np.amin((original_h, original_w))))
    resize_ratio = float(float(np.amax((original_w, original_h))) / max_side)

    if original_w >= original_h:
        new_w = max_side
        new_h = max_side/aspect_ratio
    else:
        new_h = max_side
        new_w = max_side/aspect_ratio

    resized_image = cv2.resize(image, (int(new_w), int(new_h)))
    return resized_image, resize_ratio


def hash_image(image):
    if image is None:
        return None

    m = hashlib.md5()
    m.update(image)
    url_hash = m.hexdigest()
    return url_hash


def binary_array_to_hex(arr):
    h = 0
    s = []
    for i, v in enumerate(arr.flatten()):
        if v:
            h += 2**(i % 8)
        if (i % 8) == 7:
            s.append(hex(h)[2:].rjust(2, '0'))
            h = 0
    return "".join(s)


def p_hash_image(image, hash_size=16, img_size=16):
    if image is None:
        return None

    image = Image.fromarray(image)
    image = image.convert("L").resize((img_size, img_size), Image.ANTIALIAS)
    pixels = np.array(image.getdata(), dtype=np.float).reshape((img_size, img_size))
    dct = fftpack.dct(fftpack.dct(pixels, axis=0), axis=1)
    dctlowfreq = dct[:hash_size, :hash_size]
    med = np.median(dctlowfreq)
    diff = dctlowfreq > med
    flat = diff.flatten()
    hexa = binary_array_to_hex(flat)
    return hexa


def find_face_using_dlib(image, max_num_of_faces=10):
    faces = detector(image, 1)
    faces = [[rect.left(), rect.top(), rect.width(), rect.height()] for rect in list(faces)]
    if not len(faces):
        return {'are_faces': False, 'faces': []}
    final_faces = choose_faces(image, faces, max_num_of_faces)
    return {'are_faces': len(final_faces) > 0, 'faces': final_faces}


# TODO - update function to yonatan's newest version
def choose_faces(image, faces_list, max_num_of_faces):
    # in faces w = h, so biggest face will have the biggest h (we could also take w)
    biggest_face = 0
    if not isinstance(faces_list, list):
        faces_list = faces_list.tolist()

    faces_list.sort(key=lambda x: x[3], reverse=True)  # sort the faces from big to small according to the height (which is also the width)

    relevant_faces = []
    for face in faces_list:
        if face_is_relevant(image, face):
            # since the list is reversed sorted, the first relevant face, will be the biggest
            if biggest_face == 0:
                biggest_face = face[3]
            # in case the current face is not the biggest relevant one, i'm going to check if its height smaller
            # than half of the biggest face's height, if so, the current face is not relevant and also the next
            # (which are smaller)
            else:
                if face[3] < 0.5 * biggest_face:
                    break

            relevant_faces.append(face)

    # relevant_faces = [face for face in faces_list if face_is_relevant(image, face)]

    if len(relevant_faces) > max_num_of_faces:
        score_face_local = partial(score_face, image=image)
        relevant_faces.sort(key=score_face_local)
        relevant_faces = relevant_faces[:max_num_of_faces]
    return relevant_faces


# TODO - update function to yonatan's newest version
def face_is_relevant(image, face):
    # (x,y) - left upper coordinates of the face, h - height of face, w - width of face
    # image relevant if:
    # - face bounding box is all inside the image
    # - h > 5% from the full image height
    # - h < 25% from the full image height
    # - all face (height wise) is above the middle of the image
    # - if we see enough from the body - at least 5 "faces" (long) beneath the end of the face (y + h) - we'will need to delete this condition when we'll know to handle top part of body by its own
    # - skin pixels (according to our constants values) are more than third of all the face pixels
    image_height, image_width, _ = image.shape
    x, y, w, h = face
    # threshold = face + 5 faces down = 6 faces
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCR_CB)
    face_ycrcb = ycrcb[y:y + h, x:x + w, :]
    if (x > 0 or x + w < image_width or y > 0 or y + h < image_height) \
            and 0.05 * image_height < h < 0.25 * image_height \
            and y+h < (image_height / 2)  \
            and (image_height - (h * 5)) > (y + h) \
            and is_skin_color(face_ycrcb):
        return True
    else:
        return False

# TODO : check if we actually need skin color test on faces???
def is_skin_color(face_ycrcb):
    # return True if skin pixels (according to our constants values) are more
    # than a third of all the face pixels
    h, w, _ = face_ycrcb.shape
    total_pixels_count = w*h
    if not total_pixels_count:
        return False
    skin_pixels_count = 0
    for i in range(0, h):
        for j in range(0, w):
            cond = face_ycrcb[i][j][0] > 0 and 131 < face_ycrcb[i][j][1] < 180 and 80 < face_ycrcb[i][j][2] < 130
            if cond:
                skin_pixels_count += 1
    return skin_pixels_count / float(total_pixels_count) > 0.33


# TODO - update function to yonatan's newest version
def score_face(face, image):
    image_height, image_width, _ = image.shape
    optimal_face_point = int(image_width / 2), int(0.125 * image_height)
    optimal_face_width = 0.1 * max(image_height, image_width)
    x, y, w, h = face
    face_centerpoint = x + w / 2, y + h / 2
    # This is the distance from face centerpoint to optimal centerpoint.
    positon_score = np.linalg.norm(np.array(face_centerpoint) - np.array(optimal_face_point))
    size_score = abs((float(w) - optimal_face_width))
    total_score = 0.6 * positon_score + 0.4 * size_score
    return total_score


def create_mask_for_db(image):
    if image is None:
        return None

    rect = (0, 0, image.shape[1]-1, image.shape[0]-1)
    # this is  a cv2 initializing step as presented in the demo
    bgdmodel = np.zeros((1, 65), np.float64)
    fgdmodel = np.zeros((1, 65), np.float64)

    mask = create_arbitrary_mask(image)
    cv2.grabCut(image, mask, rect, bgdmodel, fgdmodel, 1, cv2.GC_INIT_WITH_RECT)

    final_mask = np.where((mask == 1) + (mask == 3), 255, 0).astype(np.uint8)
    return final_mask


def create_arbitrary_mask(image):
    h, w = image.shape[:2]
    mask = np.zeros([h, w], dtype=np.uint8)
    sub_h = h / 20
    sub_w = w / 10
    mask[2 * sub_h:18 * sub_h, 2 * sub_w:8 * sub_w] = 2
    mask[4 * sub_h:16 * sub_h, 3 * sub_w:7 * sub_w] = 3
    mask[7 * sub_h:13 * sub_h, 4 * sub_w:6 * sub_w] = 1
    return mask


def image_is_relevant(image):
    Relevance = collections.namedtuple('Relevance', ['is_relevant', 'faces'])
    if image is not None:
        faces_dict = find_face_using_dlib(image, 4)

        if faces_dict['are_faces']:
            return Relevance(True, faces_dict['faces'])

    return Relevance(False, [])


def check_image_status(image, images_collection=IMAGES_COLLECTION):
    image_obj = db[images_collection].find_one({'image_urls': image.url},
                                               {'people.items.similar_results': 1})

    _id = None
    if image_obj:
        _id = image_obj['_id']
        if image.products_collection in image_obj['people'][0]['items'][0]['similar_results'].keys():
            status = ImageStatus.READY
            if not has_sufficient_segmentation(image_obj, image.segmentation_method):
                status = ImageStatus.RENEW_SEGMENTATION
        else:
            status = ImageStatus.ADD_COLLECTION
    elif db.iip.find_one({'image_urls': image.url}, {'_id': 1}):
        status = ImageStatus.IN_PROGRESS
    elif db.irrelevant_images.find_one({'image_urls': image.url}, {'_id': 1}):
        status = ImageStatus.NOT_RELEVANT
    else:
        status = ImageStatus.NEW_RELEVANT

    return status, _id


def has_sufficient_segmentation(image_obj, segmentation_method='pd'):
    segmentation_method = segmentation_method
    methods = [person['segmentation_method'] for person in image_obj['people']]
    return all((method == segmentation_method for method in methods))


def data_url_to_cv2_img(url):
    if url.startswith('data'):
        url = url[4:]
    nparr = np.fromstring(url.split(',')[1].decode('base64'), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

