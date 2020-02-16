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
    return None, -1


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


ocdids_not_in_db = 0
cur.execute('SELECT ocdid FROM electoral_districts')
conn.commit()
ocdids_in_db = set(row['ocdid'] for row in cur.fetchall())

def assign_ids(f):
    """Function that does the bulk of the processing. Definitely too long and
    needs to be split out to smaller functions, oh well. Outputs the
    matched data to a staging folder

    Keyword Arguments:
        f -- name of the file to process
    """
    test_file_path = os.path.join(Dirs.TEST_DIR, f)
    staging_file_path = os.path.join(Dirs.STAGING_DIR, f)

    with open(test_file_path, 'rU', encoding='utf-16') as r, \
         open(staging_file_path, 'w', encoding='utf-16') as w:
        reader = DictReader(r, dialect='excel-tab')

        try:
            rows = [row for row in reader]
        except UnicodeDecodeError:
            r = open(test_file_path, 'rU', encoding='utf-16')
            reader = DictReader(r, dialect='excel-tab')
            w = open(staging_file_path, encoding='utf-16')
            rows = [row for row in reader]

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

        for row in rows:
            row['OCDID'] = row['OCDID'].lower()
            ocdid = row['OCDID']
            if ocdid == '':
                print('{} / {} ({}) has no OCDID.'.format(row['Person UUID'],
                                                          row['Electoral District'],
                                                          row['State']))
                sys.exit()
            else:
                global ocdids_in_db
                if ocdid not in ocdids_in_db:
                        global ocdids_not_in_db
                        ocdids_not_in_db += 1
                        print('OCDID not found in database: {}'.format(ocdid))

            # Clean district names for ocdid matching
            state = (row['Electoral District']
                     if len(row['Electoral District']) == 2
                     else row['State'].lower().replace(' ', '_'))
            county = row['Body Represents - County'].lower().replace(' ', '_')
            muni = row['Body Represents - Muni'].lower().replace(' ', '_')
            ed = str(row['Electoral District'].lower())

            # Add to prefix_list in order: state, county, muni
            prefix_list = []
            if state:
                prefix_list.append('state:{}'.format(state))
            if county:
                if state in Assign.ALT_COUNTIES:
                    prefix_list.append('{}:{}'.format(Assign.ALT_COUNTIES[state],
                                                      county))
            # exception for dc
            if muni:
                if muni == 'dc':
                    prefix_list.append('district:{}'.format(muni))
                else:
                    prefix_list.append('place:{}'.format(muni))

            # ocdid_key is a tuple of the prefix list, makes matching to
            # specific group of district values only happens once
            ocdid_key = tuple(prefix_list)
            if ocdid_key in ocdid_vals:
                full_prefix = ocdid_vals[ocdid_key]['ocdid']
                ratio = ocdid_vals[ocdid_key]['ratio']
            else:
                full_prefix, ratio = get_full_prefix(prefix_list)
                ocdid_vals[ocdid_key] = {'ocdid': full_prefix, 'ratio': ratio}

            # If sub-body district (sub-county, sub-muni, etc.), add to
            # unmatched list to perform matching based on district name
            # identifiers and district count
            if is_sub_district(ed):
                d_type, d_name = get_sub_district(ed)
                unmatched_key = '{}:{}'.format(full_prefix, d_type)
                if unmatched_key not in unmatched:
                    unmatched[unmatched_key] = {'prefix': full_prefix,
                                                'districts': {},
                                                'dist_type': d_type}
                if d_name not in unmatched[unmatched_key]['districts']:
                    unmatched[unmatched_key]['districts'][d_name] = []
                unmatched[unmatched_key]['districts'][d_name].append(row)
            else:
                if full_prefix is None:
                    full_prefix = ''
                row['ocdid_report'] = Assign.REPORT_TEMPLATE.format(row['Electoral District'], full_prefix, ratio)
                # if row['OCDID'] == '':
                #   row['OCDID'] = full_prefix
                matched.append(row)

        # Match unmatched items by type and count, finding closest matches
        for k, v in unmatched.items():
            full_prefix = v['prefix']
            d_type = v['dist_type']
            districts = v['districts']
            type_val = ocdidlib.match_type(full_prefix, d_type, len(districts), districts=list(v['districts'].keys()))
            if not type_val:
                for d_name, rows in districts.items():
                    for row in rows:
                        row['ocdid_report'] = Assign.REPORT_TEMPLATE.format(row['Electoral District'], 'xxx', -1)
                        matched.append(row)
            else:
                for d_name, rows in districts.items():
                    id_val, ratio = ocdidlib.match_name(full_prefix,
                                                     type_val,
                                                     d_name)
                    if id_val is None:
                        id_val = ''
                    for row in rows:
                        row['ocdid_report'] = Assign.REPORT_TEMPLATE.format(row['Electoral District'], id_val, ratio)
                        if row['OCDID'] == '':
                            row['OCDID'] = id_val
                        matched.append(row)

        matched.sort(key=lambda x: x['Person UUID'])
        for row in matched:
            # try:
            writer.writerow(dict((k, bytearray(v, 'unicode_escape').decode('unicode_escape')) for k, v in row.items()))
            # except UnicodeDecodeError:
            #     pprint(row)

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

    files = sorted(listdir(Dirs.TEST_DIR))
    for f in files:
        if f.startswith('.') or f.startswith('_') or not f.endswith('.txt') or f.startswith('unverified'):
            continue
        elif args.state and not f.startswith(args.state):
            continue
        else:
            print(f)
            assign_ids(f)


if __name__ == '__main__':
    main()
    print('OCDIDS not in database: {}'.format(ocdids_not_in_db))
