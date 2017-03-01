from __future__ import print_function

# global libs
import requests
from cv2 import imdecode, imwrite
import logging
import os
import time
import numpy as np
import cv2
import dlib
import hashlib
from functools import partial
from jaweson import msgpack

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

# TODO - not finished yet
def url_to_img_array(url):
    if not isinstance(url, basestring):
        logging.warning("input is neither an ndarray nor a string, so I don't know what to do")
        return None

    # replace_https_with_http:
    if 'http' in url and 'https' not in url:
        url = url.replace("https", "http")
        img_url = url_or_path_to_image_file_or_cv2_image_array
        try:
            # print("trying remotely (url) ")
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(img_url, headers=headers)  # download
            img_array = imdecode(np.asarray(bytearray(response.content)), 1)
        except requests.ConnectionError:
            logging.warning("connection error - check url or connection")
            return None
        except:
            logging.warning(" error other than connection error - check something other than connection")
            return None

# TODO - not finished yet
def path_to_img_array(path):
    if not isinstance(path, basestring):
        logging.warning("input is neither an ndarray nor a string, so I don't know what to do")
        return None

# TODO - not finished yet
def download_img_array(img_array, download_path):
    filename = \
        url_or_path_to_image_file_or_cv2_image_array.split('/')[-1].split('#')[0].split('?')[-1].split(':')[-1]
    filename = os.path.join(download_directory, filename)

    if filename.endswith('jpg') or filename.endswith('jpeg') or filename.endswith('.bmp') or \
        filename.endswith('tiff'):
        pass
    else:  # there's no 'normal' filename ending so add .jpg
        filename = filename + '.jpg'

#TODO - this function need to be divided to 3
def get_cv2_img_array(url_or_path_to_image_file_or_cv2_image_array, convert_url_to_local_filename=False, download=False,
                      download_directory='images', replace_https_with_http=True):
    """
    Get a cv2 img array from a number of different possible inputs.
    :param url_or_path_to_image_file_or_cv2_image_array:
    :param convert_url_to_local_filename:
    :param download:
    :param download_directory:
    :return: img_array
    """
    got_locally = False

    # # first check if we already have a numpy array
    # if isinstance(url_or_path_to_image_file_or_cv2_image_array, np.ndarray):
    #     img_array = url_or_path_to_image_file_or_cv2_image_array

    # otherwise it's probably a string, check what kind
    elif isinstance(url_or_path_to_image_file_or_cv2_image_array, basestring):
        # try getting url locally by changing url to standard name
        if convert_url_to_local_filename:  # turn url into local filename and try getting it again
            # filename = url_or_path_to_image_file_or_cv2_image_array.split('/')[-1].split('#')[0].split('?')[0]
            # jeremy changed this since it didn't work with url -
            # https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcR2oSMcnwErH1eqf4k8fvn2bAxvSdDSbp6voC7ijYJStL2NfX6v
            # TODO: find a better way to create legal filename from url
            filename = \
                url_or_path_to_image_file_or_cv2_image_array.split('/')[-1].split('#')[0].split('?')[-1].split(':')[-1]
            filename = os.path.join(download_directory, filename)

            if filename.endswith('jpg') or filename.endswith('jpeg') or filename.endswith('.bmp') or \
                    filename.endswith('tiff'):
                pass
            else:  # there's no 'normal' filename ending so add .jpg
                filename = filename + '.jpg'

            img_array = get_cv2_img_array(filename, convert_url_to_local_filename=False, download=download,
                                          download_directory=download_directory)
            # maybe return(get_cv2 etc) instead of img_array =
            if img_array is not None:
                # print('got ok array calling self locally')
                return img_array
            else:  # couldnt get locally so try remotely
                # print('trying again remotely since using local filename didnt work, download=' + str( download) + ' fname:' + str(filename))
                return (
                    get_cv2_img_array(url_or_path_to_image_file_or_cv2_image_array, convert_url_to_local_filename=False,
                                      download=download,
                                      download_directory=download_directory))  # this used to be 'return'
        # put images in local directory
        else:
            # get remotely if its a url, get locally if not
            if "://" in url_or_path_to_image_file_or_cv2_image_array:
                if replace_https_with_http:
                    url_or_path_to_image_file_or_cv2_image_array = url_or_path_to_image_file_or_cv2_image_array.replace(
                        "https", "http")
                img_url = url_or_path_to_image_file_or_cv2_image_array
                try:
                    # print("trying remotely (url) ")
                    headers = {'User-Agent': USER_AGENT}
                    response = requests.get(img_url, headers=headers)  # download
                    img_array = imdecode(np.asarray(bytearray(response.content)), 1)
                except requests.ConnectionError:
                    logging.warning("connection error - check url or connection")
                    return None
                except:
                    logging.warning(" error other than connection error - check something other than connection")
                    return None

            else:  # get locally, since its not a url
                # print("trying locally (not url)")
                img_path = url_or_path_to_image_file_or_cv2_image_array
                try:
                    img_array = cv2.imread(img_path)
                    if img_array is not None:
                        # print("success trying locally (not url)")
                        got_locally = True
                    else:
                        # print('couldnt get locally (in not url branch)')
                        return None
                except:
                    # print("could not read locally, returning None")
                    logging.warning("could not read locally, returning None")
                    return None  # input isn't a basestring nor a np.ndarray....so what is it?
    else:
        logging.warning("input is neither an ndarray nor a string, so I don't know what to do")
        return None

    # After we're done with all the above, this should be true - final check that we're outputting a good array
    if not (isinstance(img_array, np.ndarray) and isinstance(img_array[0][0], np.ndarray)):
        print("Bad image - check url/path/array:" + str(
            url_or_path_to_image_file_or_cv2_image_array) + 'try locally' + str(
            convert_url_to_local_filename) + ' dl:' + str(
            download) + ' dir:' + str(download_directory))
        logging.warning("Bad image - check url/path/array:" + str(
            url_or_path_to_image_file_or_cv2_image_array) + 'try locally' + str(
            convert_url_to_local_filename) + ' dl:' + str(
            download) + ' dir:' + str(download_directory))
        return (None)
    # if we got good image and need to save locally :
    if download:
        if not got_locally:  # only download if we didn't get file locally
            if not os.path.isdir(download_directory):
                os.makedirs(download_directory)
            if "://" in url_or_path_to_image_file_or_cv2_image_array:  # its a url, get the bifnocho
                if replace_https_with_http:
                    url_or_path_to_image_file_or_cv2_image_array = url_or_path_to_image_file_or_cv2_image_array.replace(
                        "https", "http")
                filename = \
                    url_or_path_to_image_file_or_cv2_image_array.split('/')[-1].split('#')[0].split('?')[-1].split(':')[
                        -1]
                filename = os.path.join(download_directory, filename)
            else:  # its not a url so use straight
                filename = os.path.join(download_directory, url_or_path_to_image_file_or_cv2_image_array)
            if filename.endswith('jpg') or filename.endswith('jpeg') or filename.endswith('.bmp') or filename.endswith(
                    'tiff'):
                pass
            else:  # there's no 'normal' filename ending
                filename = filename + '.jpg'
            try:  # write file then open it
                # print('filename for local write:' + str(filename))
                write_status = imwrite(filename, img_array)
                max_i = 50  # wait until file is readable before continuing
                gotfile = False
                for i in xrange(max_i):
                    try:
                        with open(filename, 'rb') as _:
                            gotfile = True
                    except IOError:
                        time.sleep(10)
                if gotfile == False:
                    print('Could not access {} after {} attempts'.format(filename, str(max_i)))
                    raise IOError('Could not access {} after {} attempts'.format(filename, str(max_i)))
            except:  # this is prob unneeded given the 'else' above
                print('unexpected error in Utils calling imwrite')
    return img_array


def standard_resize(image, max_side):
    original_h, original_w, _  = image.shape
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
    m = hashlib.md5()
    m.update(image)
    url_hash = m.hexdigest()
    return url_hash


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
