#!/usr/bin/env python
import requests
import io
from fuzzywuzzy import fuzz, process
from operator import itemgetter
from csv import DictReader
from ocdid_config import Match, Ocdid
import unicodedata

"""
Module to parse official ocdid data accept district data, and attempt to
  match given data to official ocdids. Provides ratios data for inexact
  matches and a list of closest matches when searching

Requirements:
Python2.7
Requests
fuzzywuzzy

Constants from config:
Ocdid.URL -- location to pull ocdid data from, either a file or url
Ocdid.NONCURRENT_DIST -- set of obsolete or future districts
Match.RATIO -- lowest valid match ratio accepted
Match.LIMIT -- maximum number of matched values returned
Match.CONVERSIONS -- conversions for general district types to valid ocd types
"""


def is_ocdid(ocdid):
    """Check whether given ocdid is contained in the official ocdid list

    Keyword arguments:
    ocdid -- ocdid value to check if exists in the official ocdid list

    Returns:
    True -- ocdid exists
    False -- ocdid not found (could be candidate for new ocdid)

    """
    if ocdid in ocdid_set:
        return True
    else:
        return False


def is_exception(ocdid):
    """Check whether given ocdid is contained in the exception list

    Keyword arguments:
    ocdid -- ocdid value to check if exists in the exception list

    Returns:
    True -- ocdid exists
    False -- ocdid not found (could be candidate for new ocdid)

    """
    if ocdid in exceptions:
        return True
    else:
        return False


def get_exception(ocdid):
    """Returns official ocdid if ocdid value is in exceptions

    Keyword arguments:
    ocdid -- ocdid value to get official ocdid from exception list

    Returns:
    ocdid -- ocdid exception exists
    None -- exception not found (could be candidate for new ocdid)

    """
    if ocdid in exceptions:
        return exceptions[ocdid]
    return None


def match_name(ocdid_prefix, dist_type, dist_name):
    """Given a district name, returns closest ocdid match in given district

    Keyword arguments:
    ocdid_prefix -- ocdid section up to type value, must exist in ocdids
    dist_type -- district type value, must exist in ocdids[ocdid_prefix]
    dist_name -- district name to attempt match

    Returns:
    ocdid,ratio -- if match found, returns valid ocdid and name match ratio
    None,-1 -- if match not found, returns None for ocdid and -1 match ratio

    """
    if dist_name == 'dona_ana':
        return 'ocd-division/country:us/state:nm/county:dona_ana', 100

    # from list of districts of a given type, find the closest match
    try:
        match = process.extractOne(dist_name, ocdids[ocdid_prefix][dist_type])
    except KeyError:
        # print 'Invalid ocdid_prefix or dist_type provided'
        # print 'Prefix: {} Dist_type: {}'.format(ocdid_prefix, dist_type)
        return None, -1

    # if match fails, return empty values
    if not match:
        return None, -1
    id_val, ratio = match

    # format ocdid, check that it exists, return id value and match ratio
    ocdid = '{}/{}:{}'.format(ocdid_prefix, dist_type, id_val)

    if is_exception(ocdid):
        return get_exception(ocdid), ratio
    elif is_ocdid(ocdid):
        return ocdid, ratio
    else:
        return None, -1


def match_type(ocdid_prefix, dist_type, dist_count, **kwargs):
    """Given a district type and count, returns official ocdid district type

    Keyword arguments:
    ocdid_prefix -- ocdid section up to type value, must exist in ocdids
    dist_type -- district type value, suggested types are: park, ward, school,
                     education, commission, council, district (generic)
    dist_count -- count of districts of given type in specific geography
    kwargs['districts'] -- the actual district names from the flat file
    Returns:
    key -- if match found, returns valid ocdid and name match ratio
    'No match' -- if not match found, returns None for ocdid and -1 match ratio

    """
    # default initial values for key, district length difference, and
    key = ''
    diff_len = 1000
    type_ratio = 0

    if ocdid_prefix not in ocdids:
        return None

    
    for k, v in ocdids[ocdid_prefix].items():
        # special case for school based districts, must be explicitly requested
        if 'school' in k and dist_type != 'school':
            continue
        if 'precinct' in k and dist_type != 'precinct':
            continue
        # matches to district closest in count, using district type as a
        # secondary matching trait, 'district' is the generic type
        new_diff_len = abs(len(v)-dist_count)
        new_type_ratio = fuzz.ratio(k, dist_type)
        if new_diff_len < diff_len:
            diff_len = new_diff_len
            key = k
            type_ratio = new_type_ratio
        elif new_diff_len == diff_len and dist_type != 'district' and new_type_ratio > type_ratio:
            key = k
            type_ratio = new_type_ratio

        if kwargs['districts'] == v:
            key = k

    # district length difference must be less than 5% for a valid match
    if float(diff_len)/dist_count < .05:
        return key
    else:
        return None


def name_search(name):
    """Given a district name, searches for all matching ocdids

    ***SLOW MATCHING***
    searches everything, use a more limiting search for quicker results

    Keyword arguments:
    name -- district name to search for

    Returns:
    match_list[:MATCH_LIMIT] -- a list of the top 'MATCH_LIMIT' matches that
                                    that at least meet 'MATCH_RATIO'

    """
    match_list = []

    for prefix, district in ocdids.items():
        for dist_type, dist_names in district.items():
            # pull the closest match from each set of districts, adds to
            # match_list if > MATCH_RATIO
            match_vals = process.extractOne(name, dist_names)
            if match_vals and match_vals[1] > Match.RATIO:
                match_list.append((match_vals[1], '{}/{}:{}'.format(prefix, dist_type, match_vals[0])))

    # sorts and returns top MATCH_LIMIT matches
    match_list = sorted(match_list, key=itemgetter(0))
    match_list.reverse()
    return match_list[:Match.LIMIT]


def type_name_search(type_val, name):
    """Given a district name and type, searches for all matching ocdids

    Keyword arguments:
    type_val -- district type to search for, valid types: anc, cd, county,
                    council, village, borough, ward, township, city, court,
                    parish, state, territory, sldu, commissioner, sldl,
                    precinct, town, school, country, region, census_area
    name -- district name to search for

    Returns:
    match_list[:MATCH_LIMIT] -- a list of the top 'MATCH_LIMIT' matches that
                                    that at least meet 'MATCH_RATIO'

    """
    match_list = []

    # if type_val is standard, use the set of valid district type matches
    # otherwise accept 'all' matches
    if type_val in Match.CONVERSIONS:
        valid_dists = Match.CONVERSIONS[type_val]
    else:
        valid_dists == 'all'

    for prefix, district in ocdids.items():
        for dist_type, dist_names in district.items():
            # pull the closest match from matching sets of districts, adds to
            # match_list if > MATCH_RATIO
            if valid_dists == 'all' or dist_type in valid_dists:
                match_vals = process.extractOne(name, dist_names)
                if match_vals and match_vals[1] > Match.RATIO:
                    match_list.append((match_vals[1], '{}/{}:{}'.format(prefix, dist_type, match_vals[0])))

    # sorts and returns top MATCH_LIMIT matches
    match_list = sorted(match_list, key=itemgetter(0))
    match_list.reverse()
    return match_list[:Match.LIMIT]


def print_subdistrict_data(ocdid_prefix):
    """Given a district name, returns closest ocdid match in given district

    Keyword arguments:
    ocdid_prefix -- district name to attempt match

    """
    for k, v in ocdids[ocdid_prefix].items():
        print('  - {}:{}'.format(k, v))

""" If a url is provided, use 'requests' to obtain ocdid data
        otherwise, read from file system """
if 'http' in Ocdid.URL:
    print(Ocdid.URL)
    r = requests.get(Ocdid.URL)
    data = io.StringIO(r.text)
else:
    data = open(Ocdid.URL, 'r')
reader = DictReader(data)

""" Generate a set of only ocdid data with empty values removed """
ocdid_set = set()
ocdids = {}
exceptions = {}
for row in reader:
    if row['id'] not in Ocdid.NONCURRENT_DIST:
        # translate utf8 encodings to their closest ascii equivalent
        ocdid_set.add(row['id'])
        if row['sameAs']:
            exceptions[row['id']] = row['sameAs']

""" Create a dictionary of ocdid data in the format:
        {
            ocdid_prefix:
            {
                district_type:
                    [name_1,name_2,etc.]
            }
        }
"""
for ocdid in ocdid_set:
    prefix_div = ocdid.rfind('/')
    ocdid_prefix = ocdid[:prefix_div]
    type_val, name = ocdid[prefix_div+1:].split(':')
    if ocdid_prefix not in ocdids:
        ocdids[ocdid_prefix] = {}
    if type_val not in ocdids[ocdid_prefix]:
        ocdids[ocdid_prefix][type_val] = []
    ocdids[ocdid_prefix][type_val].append(name)
