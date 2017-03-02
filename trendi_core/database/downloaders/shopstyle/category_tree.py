# global libs
import requests
from time import sleep

# our libs
from . import constants


def build_category_tree():
    # the old version used to push the category_list immediately to the mongo and then loop and update_one
    # both for the childrenIds and the count
    # now i loop over the list locally and only in the end insert the updated category list to the mongo
    # i changed it because the old method used to make many calls to the db that are unnecessary
    # tested it and they both take about the same time with slight advantage toward the new code

    parameters = {"pid": constants.PID, "filters": "Category"}

    # download all categories
    category_list_response = requests.get(constants.BASE_URL + "categories", params=parameters)
    category_list_response_json = category_list_response.json()
    root_category = category_list_response_json["metadata"]["root"]["id"]
    category_list = category_list_response_json["categories"]

    # find all the children
    category_ids = []
    parent_ids = []
    ancestors = []

    for cat in category_list:
        category_ids.append(cat['id'])
        parent_ids.append(cat['parentId'])
        cat['children'] = []
        cat['count'] = 0
        cat['_id'] = None

    for child_idx, parent in enumerate(parent_ids):
        if parent == root_category:
            ancestors.append(category_list[child_idx])
        if category_ids.__contains__(parent):
            parent_idx = category_ids.index(parent)
            category_list[parent_idx]['children'].append(category_list[child_idx]['id'])

    # let's get some numbers in there - get a histogram for each ancestor
    for anc in ancestors:
        parameters["cat"] = anc["id"]
        response = requests.get('{}products/histogram'.format(constants.BASE_URL), parameters)
        hist = response.json()["categoryHistogram"]
        for cat in hist:
            cat_idx = category_ids.index(cat['id'])
            category_list[cat_idx]['count'] = cat['count']
        sleep(0.1)
    return category_list, ancestors
