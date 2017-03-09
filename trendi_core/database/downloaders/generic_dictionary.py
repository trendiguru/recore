from .shopstyle import constants as shopstyle_constants


def shopstyle_converter(product, gender):
    tmp_product = {}
    idx = product["id"]
    tmp_product["id"] = idx
    tmp = [i["id"] for i in product["categories"]]

    if gender is 'Female':
        relevant = shopstyle_constants.shopstyle_relevant_items_Female
        converter = shopstyle_constants.shopstyle_paperdoll_female
    else:
        relevant = shopstyle_constants.shopstyle_relevant_items_Male
        converter = shopstyle_constants.shopstyle_paperdoll_male

    cat = [cat for cat in tmp if cat in relevant]
    if len(cat) == 0:
        return None

    tmp_product["categories"] = converter[cat[0]]

    tmp_product["clickUrl"] = product["clickUrl"]
    tmp_product["images"] = {'Original': product['image']['sizes']['Original']['url'],
                             'Best': product['image']['sizes']['Best']['url'],
                             'IPhone': product['image']['sizes']['IPhone']['url'],
                             'IPhoneSmall': product['image']['sizes']['IPhoneSmall']['url'],
                             'Large': product['image']['sizes']['Large']['url'],
                             'Medium': product['image']['sizes']['Medium']['url'],
                             'Small': product['image']['sizes']['Small']['url'],
                             'XLarge': product['image']['sizes']['XLarge']['url']}
    tmp_product["status"] = {"instock": product["inStock"],
                             "hours_out": 0}
    tmp_product["shortDescription"] = product["name"]  # localized name
    tmp_product["longDescription"] = product["description"]
    tmp_product["price"] = {"price": product["price"],
                            "currency": product["currency"],
                            "priceLabel": product["priceLabel"]}

    try:
        tmp_product["brand"] = product['brand']['name']
    except:
        tmp_product["brand"] = product['brandedName']

    tmp_product["download_data"] = product["download_data"]

    return tmp_product



