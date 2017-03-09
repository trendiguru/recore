# global libs
import argparse
from datetime import datetime
from time import time, sleep
import requests
import json
import gevent
from rq import Queue
import tqdm
import copy

# our libs
from ....master_constants import db, redis_conn, redis_limit, fingerprint_version
import constants
from ...fingerprint_core import generate_mask_and_insert  # TODO
from ..generic_dictionary import shopstyle_converter
from ..annoy_dir.fanni import plantForests4AllCategories
from ..general.db_utils import refresh_similar_results

SHOPSTYLE_Q = Queue('shopstyle_fp', connection=redis_conn)


class Globals:
    def __init__(self, args):
        self.db = db
        self.collection_name = args.collection_name
        self.collection = self.db[args.collection_name]
        self.shopstyle_queries = self.db.shopstyle_queries
        self.current_dl_date = str(datetime.date(datetime.now()))
        self.last_request_time = time()
        self.fresh_download = args.fresh_download
        self.gender = args.gender
        if args.gender == 'Female':
            self.relevant = constants.shopstyle_relevant_items_Female
            self.top_category = 'womens-clothes'
        else:
            self.relevant = constants.shopstyle_relevant_items_Male
            self.top_category = 'mens-clothes'
        self.country_code = args.country_code
        self.BASE_URL = constants.BASE_URL
        if args.country_code == 'DE':
            self.BASE_URL = self.BASE_URL.replace('com', 'de')


class Query:
    def __init__(self, category, fls):
        if isinstance(category, basestring):
            self.obj_id = None
            self.category_name = category
            self.count = 3 * constants.MAX_SET_SIZE
            self.fls = fls
            self.sort = None
            self.offset = 0
            self.max_offset = 5000
        elif isinstance(category, dict):
            self.dict_2_class(category)

        else:
            assert 'bad QueryClass input - expected str/dict but got {}'.format(type(category))

    def add_sort(self, hi2lo=False):
        if hi2lo:
            self.sort = 'PriceHiLo'
            self.set_max_offset()
        else:
            self.sort = 'PriceLoHi'

    def set_max_offset(self, take_of_offset=5000):
        self.max_offset = self.count - take_of_offset

    def set_obj_id(self, idx):
        self.obj_id = idx

    def add_fls(self, new_filter):
        self.fls.append(new_filter)

    def class_2_dict(self):
        return {'category_name': self.category_name,
                'count': self.count,
                'fls': self.fls,
                'sort': self.sort,
                'offset': self.offset,
                'max_offset': self.max_offset}

    def dict_2_class(self, cat_dict):
        self.obj_id = cat_dict['_id']
        self.category_name = cat_dict['category_name']
        self.count = cat_dict['count']
        self.fls = cat_dict['fls']
        self.sort = cat_dict['sort']
        self.offset = cat_dict['offset']
        self.max_offset = cat_dict['max_offset']


def get_query_list():
    if GLOBALS.fresh_download:
        relevant_queries = create_query_list()
    else:
        relevant_queries = []
        queries = db.shopstyle_queries.find()
        for query_dict in queries:
            query = Query(query_dict, [])
            relevant_queries.append(query)

    return relevant_queries


def enqueue_or_add_filters(list_of_current_queries, candidate_query, filter_index):
    if candidate_query.count < constants.MAX_SET_SIZE:
        tmp_query = copy.deepcopy(candidate_query)
        tmp_query.set_max_offset(take_of_offset=0)
        list_of_current_queries.append(tmp_query)
        return list_of_current_queries, False
    elif candidate_query.count < 2 * constants.MAX_SET_SIZE or filter_index > 5:
        for boolean in [False, True]:
            tmp_query = copy.deepcopy(candidate_query)
            tmp_query.add_sort(hi2lo=boolean)
            list_of_current_queries.append(tmp_query)
        return list_of_current_queries, False
    else:
        return list_of_current_queries, True


def make_new_candidate_list(query, histogram_filter_idx):
    histogram_filter = constants.FILTERS[histogram_filter_idx]
    parameters = {"pid": constants.PID, "filters": histogram_filter, "cat": query.category_name}
    fls = []
    if len(query.fls) > 0:
        parameters['fl'] = query.fls
        fls = query.fls

    response = delayed_requests_get('{}products/histogram'.format(GLOBALS.BASE_URL), parameters)
    rsp = response.json()
    if histogram_filter is not 'Category':
        prefix = rsp['metadata'].get("histograms")[0].get("prefix")
    hist_name = histogram_filter.lower() + 'Histogram'
    hist = rsp[hist_name]

    queries = []
    for entry in hist:
        idx = entry['id']
        if histogram_filter is not 'Category':
            tmp_query = Query(query.category_name, fls[:])
            tmp_query.add_fls(prefix+idx)
        elif idx in GLOBALS.relevant:
            tmp_query = Query(str(idx), fls[:])
        else:
            continue
        tmp_query.count = entry['count']
        queries.append(tmp_query)

    return queries


def recursive_hist(query, hist_filter_idx, query_list):
    if hist_filter_idx > -1:
        queries = make_new_candidate_list(query, hist_filter_idx)
    else:
        queries = [query]

    for current_query in queries:
        query_list, add_filters = enqueue_or_add_filters(query_list, current_query, hist_filter_idx)

        if add_filters:
            query_list = recursive_hist(current_query, hist_filter_idx+1, query_list)

    return query_list


def create_query_list():
    top_query = Query(GLOBALS.top_category, [])
    query_list = recursive_hist(top_query, -1, [])

    list_of_dicts = [query.class_2_dict() for query in query_list]
    GLOBALS.shopstyle_queries.delete_many({})
    res = GLOBALS.shopstyle_queries.insert_many(list_of_dicts)
    for x, idx in enumerate(res.inserted_ids):
        query_list[x].set_obj_id(idx)

    return query_list


def download_query(query):
    parameters = {"pid": constants.PID, "cat": query.category_name}
    if len(query.fls) > 0:
        parameters['fl'] = query.fls

    while query.offset < query.max_offset:
        parameters['offset'] = query.offset
        product_response = delayed_requests_get(GLOBALS.BASE_URL + 'products/', parameters)
        if product_response.status_code == 200:
            product_results = product_response.json()
            total = product_results["metadata"]["total"]
            products = product_results["products"]
            products_results = [gevent.spawn(process_product, prod) for prod in products]
            gevent.joinall(products_results)
            query.offset += constants.MAX_RESULTS_PER_PAGE
            if total < query.offset:
                break
            GLOBALS.shopstyle_queries.update_one({'_id': query.obj_id}, {'$set': {'offset': query.offset}})


def process_product(product):
    # TODO - maybe use rq workers?
    product["image"] = json.loads(json.dumps(product["image"]).replace("https://", "http://"))
    product["download_data"] = {"dl_version": GLOBALS.current_dl_date}

    # case 1: new product - try to update, if does not exists, insert a new product and add our fields
    product_in_collection = GLOBALS.collection.find_one({"id": product["id"]})

    if product_in_collection is None:
        return insert_and_fingerprint(product)

    elif product_in_collection["download_data"]["fp_version"] != fingerprint_version:
        GLOBALS.collection.delete_one({'_id': product_in_collection['_id']})
        return insert_and_fingerprint(product)

    else:
        # case 2: the product was found in our db, and maybe should be modified
        status_new = product["inStock"]
        status_old = product_in_collection["status"]["instock"]
        if status_new is False and status_old is False:
            GLOBALS.collection.update_one({'_id': product_in_collection["_id"]},
                                          {'$inc': {'status.days_out': 1}})
            product["status"]["days_out"] = product_in_collection["status"]["days"] + 1
        elif status_new is False and status_old is True:
            GLOBALS.collection.update_one({'_id': product_in_collection["_id"]},
                                       {'$set': {'status.days_out': 1,
                                                'status.instock': False}})
            product["status"]["days_out"] = 1
        elif status_new is True and status_old is False:
            GLOBALS.collection.update_one({'_id': product_in_collection["_id"]},
                                          {'$set': {'status.days_out': 0,
                                                    'status.instock': True}})
            product["status"]["days_out"] = 0
        else:
            pass

        GLOBALS.collection.update_one({'_id': product_in_collection["_id"]},
                                      {'$set': {'download_data.dl_version': GLOBALS.current_dl_date}})

    return False


def insert_and_fingerprint(product):
    product = shopstyle_converter(product, GLOBALS.gender)
    if product is None:
        return False

    while SHOPSTYLE_Q.count > redis_limit:
        print ("Q full - stolling")
        sleep(600)



    product['p_hash'] = p_hash
    product['fingerprint'] = {'color': []}
    SHOPSTYLE_Q.enqueue(generate_mask_and_insert, args=(product, url, GLOBALS.current_dl_date, GLOBALS.collection_name,
                                                        image, False), timeout=1800)
    return True


def delayed_requests_get(url, params):
    global GLOBALS
    sleep_time = max(0, 0.1 - (time() - GLOBALS.last_request_time))
    sleep(sleep_time)
    GLOBALS.last_request_time = time()
    return requests.get(url, params=params)


def process_cmd_inputs():
    parser = argparse.ArgumentParser(description='"@@@ Shopstyle Download @@@')
    parser.add_argument('-c', '--countrycode', dest="country_code",
                        help='country code - currently only US or DE allowed', required=True)
    parser.add_argument('-g', '--gender', dest="gender",
                        help='specify which gender to download. (Female or Male - case sensitive)', required=True)
    parser.add_argument('-f', '--fresh', dest="fresh_download", action='store_true',
                        help='add this flag for a new category build')
    args = parser.parse_args()

    if args.gender in ['Female', 'Male'] and args.country_code in ["US", "DE"]:
        args.collection_name = "shopstyle_{}_{}".format(args.country_code, args.gender)
        print ("@@@ Shopstyle Download @@@\nyou choose to update the " + args.collection_name + " collection")
    else:
        assert "bad input - gender should be only Female or Male (case sensitive)"
    return args


if __name__ == '__main__':

    cmdArgs = process_cmd_inputs()
    GLOBALS = Globals(cmdArgs)

    print ("{} Update Started at {}".format(GLOBALS.collection_name, datetime.now().replace(microsecond=0)))
    shopstyleQueries = get_query_list()

    current_category = ''
    for shopstyleQuery in tqdm.tqdm(shopstyleQueries):
        download_query(shopstyleQuery)

    GLOBALS.collection.delete_many({'fingerprint': {"$exists": False}})

    forest = Queue('annoy_forest', connection=redis_conn)

    forest_job = forest.enqueue(plantForests4AllCategories, col_name=GLOBALS.collection_name, timeout=3600)
    while not forest_job.is_finished and not forest_job.is_failed:
        sleep(300)
    if forest_job.is_failed:
        print ('annoy plant forest failed')

    if GLOBALS.gender == 'Male':
        refresh_similar_results(GLOBALS.collection_name)

    print ("{} Update Finished at {}".format(GLOBALS.collection_name, datetime.now().replace(microsecond=0)))

'''
pseudo code:
1. get user inputs
2. make a list of queries - recursive function
    2.1 create category tree
    2.2 for cat in tree: find parents and children (only relevant)
    2.3 from the top down(only for top categories - not women or women-clothes and etc...) :
        if count < MAX:
            insert query to list
        elif count < 2*MAX:
            insert 2 queries to list
                1- with sort PriceLoHi
                2- with sort PriceHiLo + max-offset = count - 5050
        else
        2.3.1 create queries by Price
            2.3.1.1 if Prices > MAX:
                        create queries for Color
                2.3.1.1.1 if Price+Color > MAX:
                            create queries for Discount
                    2.3.1.1.1 if Price+Color+Discount > MAX:
                                sort by PriceLoHi/PriceHiLo
                                if not < 2*MAX - create query by children

    2.4 for query in queries : download from offset = 0 to offset = total
        2.4.1 update query_collection for offset
        2.4.2 generic_dict
    2.5 remove old items (archive)
    2.6 annoy/nmslib
'''
