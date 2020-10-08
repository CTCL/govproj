#!/usr/bin/env python3

import sys
sys.path.append('old_processing')
from csv import DictReader, DictWriter
from importlib.machinery import SourceFileLoader
from os import listdir
import ocdid as ocdidlib
import os.path
from argparse import ArgumentParser
from process_config import Dirs, Assign
from pprint import pprint
import importlib
import io
import psycopg2
import psycopg2.extras
import re

try:
    config = SourceFileLoader('config', 'config.py').load_module()
except IOError:
    raise Exception('Error: Config file not found.')

conn = psycopg2.connect(database=config.sql['database'],
                        host=config.sql['host'],
                        user=config.sql['user'],
                        password=config.sql['password'])
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute('SET search_path=vip')
conn.commit()
print('Connected to database')

"""
Assign ocdids by grouping data from each state and matching them to official
  ocdid values. Districts at a state, county, or city level are matched
  directly to that ocdid level. Sub-districts within each of these are grouped
  and then matched based on district count and name similarity

Requirements:
    Python2.7
    ocdid module (+ module requirements)

Constants:
    Dirs.TEST_DIR -- Directory where raw data is stored
    Dirs.STAGING_DIR -- Directory to place files after matching to ocdids
    Assign.OCD_PREFIX -- Prefix for all ocdids: 'ocd-division/country:us/'
    Assign.ALT_COUNTIES -- alternative county types, LA parish, AK borough
    Assign.REPORT_TEMPLATE -- string template for match reports
    Assign.DIST_TYPES -- check for district types in order
    Assign.SPLIT_TYPES -- strings to split types and values on
"""


def is_exact(prefix_list):
    """Determines if there is an exact match to an ocdid

    Keyword Arguments:
        prefix_list -- list of district values for the ocdid

    Returns:
        ocdid -- if found returns the exact match, otherwise returns None
    """
    test_id = Assign.OCD_PREFIX + '/'.join(prefix_list)
    if ocdidlib.is_ocdid(test_id):
        return test_id
    return None


def match_exists(prefix_list, offset):
    """Given a district list and offset value, determines if a match exists
    for that ocdid

    Keyword Arguments:
        prefix_list -- list of district values for the ocdid
        offset -- district level to check against
                  (ex. 1 - one additional level, 2 - two levels, etc.)

    Returns:
        ocdid -- matching full ocdid if match found, otherwise None
        ratio -- ratio of that exact match (1-100), returns -1 if not found
    """
    new_prefix = is_exact(prefix_list[:offset])
    if new_prefix:
        dist_type, dist_name = prefix_list[offset].split(':')
        return ocdidlib.match_name(new_prefix, dist_type, dist_name)
    return None, -1


def get_full_prefix(prefix_list):
    """When provided a district list, searches a returns to closest ocdid
    match for that district and the text match ratio

    Keyword arguments:
        prefix_list -- list of district values for the ocdid

    Returns:
        id_val -- full valid ocdid value
        ratio -- match ratio of district name provided to ocdid name
    """

    # If the list is empty, it's just the country:us ocdid
    if len(prefix_list) == 0:
        return 'ocd-division/country:us', 100

    # NY City/Villages have exceptions since there can be cities, villages,
    # and towns with the same name in the same county
    if prefix_list[-1].startswith('place:city_of_') or prefix_list[-1].startswith('place:village_of_'):
        prefix_list.pop(-2)
        prefix_list[-1] = prefix_list[-1].replace('city_of_', '')
        prefix_list[-1] = prefix_list[-1].replace('village_of_', '')

    # Check if there is an immediate exact match. If so, return with a ratio
    # of 100
    id_val = is_exact(prefix_list)
    if id_val:
        return id_val, 100

    # Check for a closely similar match if no exact match exists
    if len(prefix_list) > 1:
        id_val, ratio = match_exists(prefix_list, -1)
        if ratio >= 91:
            return id_val, ratio

    # Try removing district values from list to find a match. For example, a
    # city district might be state->city element instead of state->county->city
    if len(prefix_list) > 2:
        id_val, ratio = match_exists(prefix_list, -2)
        if ratio <= 91:
            return None, -1
        prefix_list[-2] = id_val.split('/')[-1]

        id_val = is_exact(prefix_list)
        if id_val:
            return id_val, 100

        id_val, ratio = match_exists(prefix_list, -1)
        if ratio >= 91:
            return id_val, ratio
        else:
            prefix_list.pop(-2)
            id_val = is_exact(prefix_list)
            if id_val:
                return id_val, 100
            id_val, ratio = match_exists(prefix_list, -1)
            if ratio >= 91:
                return id_val, ratio
    # Return None and -1 for the ratio if no match is found
    return id_val, -1


def is_sub_district(e_district):
    """Determines if a district name is describing a lower level district
    than what is provide by the 'Body Represents' info, such as a county
    commission district, ward, etc.

    Keyword Arguments:
        e_district -- name of the electoral district

    Returns:
        True -- if district is a lower level district
        False -- if 'Body Represents' info sufficient to place district
    """
    if 'precinct ' in e_district or 'district ' in e_district:
        return True
    # 'ward' logic here to avoid capturing stuff like 'Ward County'
    elif ' ward ' in e_district or (e_district.startswith('ward ') and len(e_district) < 9):
        return True
    else:
        return False


def get_sub_district(e_district):
    """Returns the type value for the lower level district by splitting the
    district name using the given split values into its type and value

    Keyword Arguments:
        e_district -- name of the electoral district

    Returns:
        dist_type -- formalized district type name
        e_district -- split district value (council district 3 -> value 3)
    """
    # Iterate through main district types, break if matching type found
    for t in Assign.DIST_TYPES:
        if t in e_district:
            if t == 'house' or t == 'assembly':
                dist_type = 'sldl'
            elif t == 'senate':
                dist_type = 'sldu'
            else:
                dist_type = t
            break
    # Iterate through split types, use type to split district type from value
    # if found
    for s in Assign.SPLIT_TYPES:
        if s in e_district:
            return dist_type, e_district.split(s)[-1].strip().replace(' ', '_')


cur.execute('SELECT ocdid FROM electoral_districts')
ocdids_in_db = set(row['ocdid'] for row in cur.fetchall())
conn.commit()

def assign_ids(f):
    """Function that does the bulk of the processing. Definitely too long and
    needs to be split out to smaller functions, oh well. Outputs the
    matched data to a staging folder

    Keyword Arguments:
        f -- name of the file to process
    """
    test_file_path = os.path.join(Dirs.TEST_DIR, f)
    staging_file_path = os.path.join(Dirs.STAGING_DIR, f)

    with open(test_file_path, 'r', encoding='utf-16') as r, \
         open(staging_file_path, 'w', encoding='utf-16') as w:
        reader = DictReader(r, dialect='excel-tab')
        rows = list(reader)
        fields = reader.fieldnames
        # ocdid_report is not included sometimes, and additional fields are
        # occassionally added.
        if 'ocdid_report' not in fields:
            fields.append('ocdid_report')
        writer = DictWriter(w, fieldnames=fields, dialect='excel-tab')
        writer.writeheader()

        ocdid_vals = {}
        unmatched = {}
        matched = []

        for row in list(rows):
            row['OCDID'] = row['OCDID'].lower()
            ocdid = row['OCDID']
            if ocdid == '':
                message = '{} / {} ({}) has no OCDID.'
                print(message.format(row['Person UUID'],
                                     row['Electoral District'],
                                     row['State']))
                rows.remove(row)

            matched.append(row)

        matched.sort(key=lambda x: x['Person UUID'])
        try:
            writer.writerows(matched)
        except ValueError:
            print(matched[0])
            print([match for match in matched if None in list(match)][0])
            raise

def main():
    """Pull in file list and assign id's to each file. Accepts the -s
    command line option to only assign data to a specific state or file
    abbreviation ('SL', 'SW', 'City', state abbreviations, etc.)
    """

    usage = 'Assign ocdids to office holders'
    parser = ArgumentParser(usage=usage)
    parser.add_argument('-s', action='store', dest='state',
                        default=None, help='Abbreviation of state to assign')
    args = parser.parse_args()

    filenames = [filename for filename in sorted(listdir(Dirs.TEST_DIR))
                 if filename.endswith('.txt')]
    for filename in filenames:
            print(filename)
            assign_ids(filename)


if __name__ == '__main__':
    main()
