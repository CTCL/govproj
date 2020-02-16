import os.path
import re
from datetime import datetime


class Dirs(object):
    # Change directory to match installation:
    BASE_DIR     = '/path/to/govproj/csv'
    # Do not edit below this line!

    TEST_DIR     = os.path.join(BASE_DIR, 'collection')
    STAGING_DIR  = os.path.join(BASE_DIR, 'staging')
    PROD_FF      = os.path.join(BASE_DIR, 'production/flat_files')
    PROD_JSON    = os.path.join(BASE_DIR, 'production/json')
    REPORTS_DIR  = os.path.join(BASE_DIR, 'reports')
    JSON_VERSION = os.path.join(
        BASE_DIR,
        'json',
        '{}'.format(datetime.now().strftime('%Y-%m-%d'))
    )
    DATE_VAL     = str(datetime.now()).replace(' ', '_')
    DATE_VAL     = DATE_VAL[:DATE_VAL.find('.')]
    SUMMARY      = '{}/summary_report_{}.csv'.format(REPORTS_DIR, DATE_VAL)
    NEW_DIST     = '{}/new_districts_{}.csv'.format(REPORTS_DIR, DATE_VAL)
    QUESTIONS    = '{}/questionable_matches_{}.csv'.format(REPORTS_DIR, DATE_VAL)
    ISSUES       = '{}/non_ocdid_issues_{}.csv'.format(REPORTS_DIR, DATE_VAL)
    URL_FILE = '{}/url_report_{}.csv'.format(REPORTS_DIR, DATE_VAL)
    SUMMARY_FIELDS = ['state', 'unique_districts', 'non_ocdid_issues',
                      'new_ocdids', 'questionable_ocdid_matches',
                      'unique_urls']
    NEW_DIST_FIELDS = ['state', 'uid', 'county', 'muni', 'office_level',
                       'electoral_district', 'office_name']
    QUESTIONS_FIELDS = ['state', 'uid', 'county', 'muni', 'office_level',
                        'electoral_district', 'office_name', 'ocdid', 'ratio']
    ISSUES_FIELDS = ['state', 'uid', 'element', 'issue', 'element_data',
                     'electoral_district', 'office_name', 'ocdid']
    URL_FIELDS = ['UID', 'line_number', 'element', 'issue']


class Assign(object):
    OCD_PREFIX = 'ocd-division/country:us/'
    ALT_COUNTIES = {'la': 'parish', 'ak': 'borough'}
    REPORT_TEMPLATE = u'District: {} OCDID: {} Ratio: {}'
    DIST_TYPES = ['ward', 'school', 'precinct', 'council',
                  'park', 'commission', 'house', 'assembly',
                  'senate', 'district']
    SPLIT_TYPES = ['precinct', 'district', 'ward']


class Validate(object):
    EMAIL = re.compile(r'[A-Z0-9._\'%-]+@[A-Z0-9.-]+\.[A-Z]{2,4}',
                       re.IGNORECASE)
    TWITTER = re.compile(r'[A-Z0-9_]+', re.IGNORECASE)
    REGEX_CHECKS = {'Email': EMAIL,
                    'Twitter Name': TWITTER}
    URL_CHECKS = {'Facebook URL': 'facebook.com'}
    NON_URL_CHECKS = {'Wiki Word': 'wikipedia.org/',
                      'Youtube': 'youtube.com'}


class NewJson(object):
    OPTIONAL_OFF = {'Body Represents - County': 'body_represents_county',
                    'Body Represents - Muni': 'body_represents_muni',
                    'Source': 'source'}
    OPTIONAL_OH = {'Source': 'source',
                   'Official Party': 'party',
                   'Phone': 'phone',
                   'Mailing Address': 'mailing_address',
                   'Wiki Word': 'wiki_word',
                   'Youtube': 'youtube',
                   'DOB': 'dob'}
