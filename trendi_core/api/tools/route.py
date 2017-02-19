# global libs
from ..constants import products_per_ip_pid
import maxminddb

geo_db_path = '/usr/local/lib/python2.7/dist-packages/maxminddb'
geo_reader = maxminddb.open_database(geo_db_path + '/GeoLite2-Country.mmdb')


def get_country_from_ip(ip):
    user_info = geo_reader.get(ip)
    if user_info:
        if 'country' in user_info.keys():
            return user_info['country']['iso_code']
        elif 'registered_country' in user_info.keys():
            return user_info['registered_country']['iso_code']
    else:
        return None


def get_collection_from_ip_and_pid(ip, pid='default'):
    country = 'default' if not ip else get_country_from_ip(ip)
    default_map = products_per_ip_pid['default']
    if pid in products_per_ip_pid.keys():
        pid_map = products_per_ip_pid[pid]
        if country:
            if country in pid_map.keys():
                return pid_map[country]
            elif 'default' in pid_map.keys():
                return pid_map['default']
            else:
                if country in default_map.keys():
                    return default_map[country]
                else:
                    return default_map['default']
        else:
            if 'default' in pid_map.keys():
                return pid_map['default']
            else:
                return default_map['default']
    else:
        if country in default_map.keys():
            return default_map[country]
        else:
            return default_map['default']

