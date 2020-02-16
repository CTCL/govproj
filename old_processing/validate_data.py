#!/usr/bin/env python

from argparse import ArgumentParser
from csv import DictReader, DictWriter
from os import listdir
from pprint import pprint
from process_config import Validate, Dirs
from us.states import STATES as states
import os.path
import requests
import re
import sys

"""
Script to validate staging data and move valid data to the production
  directory. Each field in each file is checked to make sure it is valid
  (urls, twitter handles, facebook pages are in the proper format, phones
  and emails are at least textually valid, etc.). An option is also provided
  to check all URLs to make sure they return valid status codes.

Constants:
    Dirs.STAGING_DIR -- directory for staging data
    Dirs.PROD_FF -- production directory for flat file information
    Dirs.SUMMARY -- summary file name in reports directory
    Dirs.QUESTIONS -- questionable matches file name in reports directory
    Dirs.ISSUES -- issues file name in reports directory
    Dirs.URL_FILE -- url validation file name in reports directory
    Dirs.SUMMARY_FIELDS -- fields for summary report file
    Dirs.NEW_DIST_FIELDS -- fields for new districts file
    Dirs.QUESTIONS_FIELDS -- fields for questionable matches file
    Dirs.ISSUES_FIELDS -- fields for non-ocdid issues file
    Dirs.URL_FIELDS -- fields for url validation file
    Validate.REGEX_CHECKS -- regular expression checks (twitter, email)
    Validate.URL_CHECKS -- fields to make sure contain full urls
    Validate.NON_URL_CHECKS -- fields that should not contain url information
"""

# Data structure to aggregate counts of listed fields
agg = {'Facebook URL': {'set_vals': set(), 'dups': 0},
       'Twitter Name': {'set_vals': set(), 'dups': 0},
       'Website (Official)': {'set_vals': set(), 'dups': 0},
       'Email': {'set_vals': set(), 'dups': 0},
       'Wiki Word': {'set_vals': set(), 'dups': 0},
       'DOB': {'set_vals': set(), 'dups': 0},
       'Official Name': {'set_vals': set(), 'dups': 0},
       'Official Party': {'set_vals': set(), 'dups': 0},
       'Phone': {'set_vals': set(), 'dups': 0}}


def url_response(url):
    """Makes a request to a url to determine if the url is valid

    Keyword Arguments:
        url -- url to check

    Returns:
        url -- url checked
        response -- response code if request successful, otherwise 'bad'
    """
    try:
        r = requests.get(url)
        return {'url': url, 'response': r.status_code}
    except:
        return {'url': url, 'response': 'bad'}


def validate(f, u):
    """A really ridiculous functions that performs all the validations
    under the sun to each field in the data. Definitely should not have
    structured the code like I did, but it's too late now. Comments throughout
    the function to explain what the hell is going on. Possibly should have
    made functions for each validation.

    Keyword Arguments:
        f -- file to validate
        u -- flag to indicate whether to make requests to each url

    Returns:
        summary -- data for summary file
        new_dist -- data for new districts matches file
        questions -- data for questionable matches file
        issues -- data for non-ocdid issues file
    """

    new_dist = {}
    questions = []
    issues = []

    row_count = 1
    error_count = 0
    urls = set()
    districts = set()
    state = f.split()[0]

    print(f)
    # open each file in this function (don't know why I coded it this way)
    staging_file_path = os.path.join(Dirs.STAGING_DIR, f)
    production_file_path = os.path.join(Dirs.PROD_FF, f)
    r = open(staging_file_path, 'r', encoding='utf-16')
    w = open(production_file_path, 'w', encoding='utf-16')
    reader = DictReader(r, dialect='excel-tab')
    try:
        rows = [row for row in reader]
    except UnicodeDecodeError:
        r = open(staging_file_path, 'rU', encoding='utf-16')
        reader = DictReader(r, dialect='excel-tab')
        rows = [row for row in reader]
        w = open(production_file_path, 'w', encoding='utf-16')

    writer = DictWriter(w, fieldnames=reader.fieldnames[:-1],
                        extrasaction='ignore',
                        dialect='excel-tab')
    writer.writeheader()

    for row in rows:
        row_count += 1
        districts.add(row['OCDID'])

        # If a website is provide, it is invalid if it doesn't have the
        # full url (starts with http/https). A lot of facebook urls were
        # listed in this column, so I wrote an additional check for those
        if row['Website (Official)']:
            site = row['Website (Official)'].lower().strip()
            if not(site.startswith('http:') or site.startswith('https:')):
                error_count += 1
                issues.append({'state': state,
                               'uid': row['Person UUID'],
                               'element': 'Website (Official)',
                               'issue': 'Must start with http:// or https://',
                               'element_data': row['Website (Official)'],
                               'electoral_district': row['Electoral District'],
                               'office_name': row['Office Name'],
                               'ocdid': row['OCDID']})
            elif site.find('facebook.com') >= 0:
                error_count += 1
                issues.append({'state': state,
                               'uid': row['Person UUID'],
                               'element': 'Website (Official)',
                               'issue': 'facebook.com in Website URL',
                               'element_data': row['Website (Official)'],
                               'electoral_district': row['Electoral District'],
                               'office_name': row['Office Name'],
                               'ocdid': row['OCDID']})
            else:
                urls.add(row['Website (Official)'])

        # For twitter usernames and emails, validate against a regex
        for field, regex in Validate.REGEX_CHECKS.items():
            if field == 'Twitter Name' and field not in row:
                field = 'Twitter Name (Gov)'
            row[field] = row[field].strip()

            if row[field] and not(regex.match(row[field])):
                error_count += 1
                issues.append({'state': state,
                               'uid': row['Person UUID'],
                               'element': field,
                               'issue': 'Invalid {0}'.format(field),
                               'element_data': row[field],
                               'electoral_district': row['Electoral District'],
                               'office_name': row['Office Name'],
                               'ocdid': row['OCDID']})
        # certain fields, such as wiki word, should not contain the full
        # wikipedia url
        for field, val in Validate.NON_URL_CHECKS.items():
            if field == 'Facebook URL' and field not in row:
                field = 'Facebook URL (Gov)'
            row[field] = row[field].strip()

            if row[field] and row[field].find(val) != -1:
                error_count += 1
                issues.append({'state': state,
                               'uid': row['Person UUID'],
                               'element': field,
                               'issue': '{0} contains {1}'.format(field, val),
                               'element_data': row[field],
                               'electoral_district': row['Electoral District'],
                               'office_name': row['Office Name'],
                               'ocdid': row['OCDID']})
        # certain fields, such as facebook, had to contain 'facebook.com'
        # as part of the url
        for field, url in Validate.URL_CHECKS.items():
            if field == 'Facebook URL' and field not in row:
                field = 'Facebook URL (Gov)'
            row[field] = row[field].strip()

            if row[field] and row[field].find(url) == -1:
                error_count += 1
                issues.append({'state': state,
                               'uid': row['Person UUID'],
                               'element': field,
                               'issue': '{0} missing from {1}'.format(url, field),
                               'element_data': row[field],
                               'electoral_district': row['Electoral District'],
                               'office_name': row['Office Name'],
                               'ocdid': row['OCDID']})

        # if an ocdid was provided, check to see if the ratio was either
        # not found (-1) or questionable (less than 100 or 'xxx')
        if len(row['OCDID']) > 0:
            ocdid_report = row['ocdid_report']
            ratio = ocdid_report.split(':')[-1].strip()
            if ratio == '-1':
                new_dist_hash = hash(row['Body Represents - County']+row['Electoral District'])
                if new_dist_hash not in new_dist:
                    new_dist[new_dist_hash] = {'state': state,
                                               'uid': row['Person UUID'],
                                               'county': row['Body Represents - County'],
                                               'muni': row['Body Represents - Muni'],
                                               'office_level': row['Office Level'],
                                               'electoral_district': row['Electoral District'],
                                               'office_name': row['Office Name']}
            elif ratio != '100' and ratio != 'xxx':
                questions.append({'state': state,
                                  'uid': row['Person UUID'],
                                  'county': row['Body Represents - County'],
                                  'muni': row['Body Represents - Muni'],
                                  'office_level': row['Office Level'],
                                  'electoral_district': row['Electoral District'],
                                  'office_name': row['Office Name'],
                                  'ocdid': row['OCDID'],
                                  'ratio': ratio})
        else:
            new_dist_hash = hash(row['Body Represents - County']+row['Electoral District'])
            if new_dist_hash not in new_dist:
                new_dist[new_dist_hash] = {'state': state,
                                           'uid': row['Person UUID'],
                                           'county': row['Body Represents - County'],
                                           'muni': row['Body Represents - Muni'],
                                           'office_level': row['Office Level'],
                                           'electoral_district': row['Electoral District'],
                                           'office_name': row['Office Name']}
        # aggregate all unique results, write to terminal at the end
        for k, v in agg.items():
            if k == 'Office Names':
                row['Office Names'] = ' '.join(row['Office Name'].lower().split('district ')[:-1]).strip()
                row_k = k
            elif k == 'Twitter Name' and k not in row:
                row_k = 'Twitter Name (Gov)'
            elif k == 'Facebook URL' and k not in row:
                row_k = 'Facebook URL (Gov)'
            else:
                row_k = k

            if row.get(row_k):
                val = row[row_k].lower().strip()
                if val in agg[k]['set_vals']:
                    agg[k]['dups'] += 1
                else:
                    agg[k]['set_vals'].add(val)

        office_name = row['Office Name']
        if re.match(r'^[A-Z]{2}(?: Lieutenant)? Governor$', office_name):
            match = re.match(r'^([A-Z]{2})((?: Lieutenant)? Governor)$',
                             office_name)
            state_abbrev = match.group(1)
            office_base = match.group(2).strip()
            state_name = next(iter(state for state in states
                                   if state.abbr == state_abbrev)).name
            row['Office Name'] = '{} of {}'.format(office_base, state_name)

        level = row['Office Level']
        role = row['Office Role']
        jurisdiction = row.get('Jurisdiction') or ''
        ocdid = row['OCDID']

        if level == 'locality':
            new_level = 'City'
        elif level == 'country':
            if role == 'legislatorLowerBody':
                new_level = 'Federal - Lower'
            elif role == 'legislatorUpperBody':
                new_level = 'Federal - Upper'
            else:
                new_level = 'Federal'
        elif level == 'administrativeArea1':
            if role == 'legislatorLowerBody':
                new_level = 'State Legislature Lower'
            elif role == 'legislatorUpperBody':
                new_level = 'State Legislature Upper'
            else:
                new_level = 'State'
        elif level == 'administrativeArea2':
            if jurisdiction.lower().endswith('borough'):
                new_level = 'Borough'
            elif jurisdiction.lower().endswith('parish'):
                new_level = 'Parish'
            elif (jurisdiction.lower().endswith('city')
                  or '/place:' in ocdid):
                new_level = 'City'
            elif '/region:' in ocdid:
                new_level = 'Regional'
            elif (jurisdiction.lower().endswith('county')
                  or row['Electoral District'].lower().endswith('county')
                  or '/county:' in ocdid):
                new_level = 'County'
            else:
                pprint(row)
                sys.exit()
        elif level == 'regional':
            new_level = 'Regional'
        elif level in ('City',):
            new_level = level

        row['Office Level'] = new_level

        writer.writerow(row)
    r.close()
    w.close()

    # if the url flag was provided, make a request and check response code for
    # each url. Should be threaded, gave up after 4 attempts.
    if u:
        with open(Dirs.URL_FILE, 'a', encoding='utf-16') as w:
            writer = DictWriter(w, fieldnames=Dirs.URL_FIELDS,
                                dialect='excel-tab')
            print('Checking URL response codes...')
            results = []
            url_counter = 0
            for url in urls:
                url_counter += 1
                if url_counter % 100 == 0:
                    print(url_counter)
                results.append(url_response(url))
            for r in results:
                if r['response'] != 200:
                    writer.writerow({'UID': 'xxx',
                                     'line_number': 'xxx',
                                     'element': 'URL',
                                     'issue': '{0} returns: {1}'.format(r['url'], r['response'])})

    summary = {'state': state,
               'unique_districts': len(districts),
               'non_ocdid_issues': error_count,
               'new_ocdids': len(new_dist),
               'questionable_ocdid_matches': len(questions),
               'unique_urls': len(urls)}

    return summary, new_dist, questions, issues


def main():
    """Main function creates a new summary, districts, questionable matches,
    and issues file, validates each file, and moves staging data to production
    """
    usage = 'Validate Governance Project Data'
    parser = ArgumentParser(usage=usage)

    parser.add_argument('-u', '--urlcheck',
                        action='store_true', dest='urls',
                        help='Flag to check response codes for all urls')

    args = parser.parse_args()
    summary = []

    with open(Dirs.SUMMARY, 'w', encoding='utf-16') as sw, \
         open(Dirs.NEW_DIST, 'w', encoding='utf-16') as ndw, \
         open(Dirs.QUESTIONS, 'w', encoding='utf-16') as qw, \
         open(Dirs.ISSUES, 'w', encoding='utf-16') as iw:
        summary_writer = DictWriter(sw, fieldnames=Dirs.SUMMARY_FIELDS,
                                    dialect='excel-tab')
        new_dist_writer = DictWriter(ndw, fieldnames=Dirs.NEW_DIST_FIELDS,
                                     dialect='excel-tab')
        questions_writer = DictWriter(qw, fieldnames=Dirs.QUESTIONS_FIELDS,
                                      dialect='excel-tab')
        issues_writer = DictWriter(iw, fieldnames=Dirs.ISSUES_FIELDS,
                                   dialect='excel-tab')

        summary_writer.writeheader()
        new_dist_writer.writeheader()
        questions_writer.writeheader()
        issues_writer.writeheader()

        filenames = [filename for filename in sorted(listdir(Dirs.STAGING_DIR))
                     if filename.endswith('.txt')]
        for filename in filenames:
            summary, new_dist, questions, issues = validate(filename, args.urls)
            summary_writer.writerow(summary)
            for q in questions:
                questions_writer.writerow(q)
            for i in issues:
                issues_writer.writerow(i)
            for k, v in new_dist.items():
                new_dist_writer.writerow(v)
        for k, v in agg.items():
            print('{}: unique: {}  duplicates: {}'.format(k, len(v['set_vals']), v['dups']))


if __name__ == '__main__':
    main()
