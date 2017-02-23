#!/usr/bin/env python

from argparse import ArgumentParser
from collections import Counter
from difflib import SequenceMatcher
from nameparser import HumanName
from pprint import pprint
from unidecode import unidecode
from validate_email import validate_email
import argparse
import csv
import itertools
import nameparser.config
import re
import phonenumbers

nameparser.config.CONSTANTS.string_format = '{first} {last}'

arg_parser = ArgumentParser(prog='validate_csv.py',
                            description='Validate a GovProj CSV file.')
arg_parser.add_argument('state')

args = vars(arg_parser.parse_args())

csv_path = 'data/collection/{state} Office Holders.csv'.format(state=args['state'])
csv_file = open(csv_path)
reader = csv.DictReader(csv_file)
csv_rows = [row for row in reader]


def simplify_name(candidate_name):
    try:
        simplified = HumanName(candidate_name.strip().lower())
        simplified.capitalize()
    except UnicodeDecodeError:
        simplified = candidate_name

    return str(simplified)


def simplify_district(district):
    return re.sub(r'District (?:Area|Zone|Place|Precinct|Division)',
                  'District',
                  district.title())


def bare_string(string):
    return re.sub(' {2,}', ' ', re.sub(r'[^\w ]', '', string)).strip().lower()


for row in csv_rows:
    for column in reader.fieldnames:
        row[column] = row[column].strip()

    try:
        row['Simplified Name'] = simplify_name(row['Official Name'])
    except UnicodeDecodeError:
        row['Simplified Name'] = row['Official Name'].lower().strip()


candidate_names = [row['Simplified Name'] for row in csv_rows
                   if not re.search(r'\?|candidate|pending|\bno\b|^$',
                                    row['Official Name'].strip(),
                                    flags=re.IGNORECASE)]

candidate_uuids = [row['Person UUID'] for row in csv_rows if row['Person UUID'] != '']
dupe_uuids = set(uuid for uuid, count in
                 Counter(candidate_uuids).items() if count > 1)
reported_dupe_uuids = []

try:
    internal_ids = [row['ID'] for row in csv_rows if row['ID'] != '']
    dupe_internal_ids = set(internal_id for internal_id, count in
                            Counter(internal_ids).items() if
                            count > 1)
except KeyError:
    dupe_internal_ids = set()

reported_dupe_internal_ids = []

office_names = set([bare_string(row['Office Name']) for row in csv_rows if
                    row['Office Name'].strip() != ''])

suspected_dupe_candidates = set([candidate for candidate, count in
                                 Counter(candidate_names).items() if
                                 count > 1 and candidate not in (
                                     'Bobby Strunk', 'Harry Percey'
                                 )])

reported_dupe_candidates = []
reported_multiple_office_names_uuids = []
reported_multiple_body_names_uuids = []
reported_multiple_categories_uuids = []
reported_multiple_levels_uuids = []
reported_multiple_roles_uuids = []
reported_candidate_uuids_with_no_office_uuids = []
reported_inconsistent_partisanship_uuids = []
reported_multiple_uuids_for_office = []

office_uuids = list(set(row['UID'] for row in csv_rows))
counts_by_office_uuid = {
    uuid: {
        'Office Name': len(set(row['Office Name'] for row in csv_rows
                               if row['UID'] == uuid)),
        'Office Category': len(set(row['Office Category'] for row in csv_rows
                                   if row['UID'] == uuid)),
        'Body Name': len(set(row['Body Name'] for row in csv_rows
                             if row['UID'] == uuid)),
        'Office Level': len(set(row['Office Level'] for row in csv_rows
                         if row['UID'] == uuid)),
        'Office Role': len(set(row['Office Role']
                        for row in csv_rows
                        if row['UID'] == uuid)),
    } for uuid in office_uuids
}


def office_string(row):
    return '; '.join(filter(None, [row['Office Name'], row.get('County'),
                                   row['Electoral District']]))

#print office_string(csv_rows[0])

offices = list(set(office_string(row) for row in csv_rows))
uuids_by_office = {
    office: list(set([row['UID'] for row in csv_rows if
                      office_string(row) == office and
                      row['UID'] != '']))
    for office in offices
}

parties_by_office_uuid = {
    uuid: list(set(row['Official Party'] for row in csv_rows
                   if row['UID'] == uuid))
    for uuid in office_uuids
}


def office_has_multiple_uuids(office):
    uuids = uuids_by_office[office]
    if len(uuids) > 1 and \
       not any(uuid in reported_multiple_uuids_for_office
               for uuid in uuids):
        for uuid in uuids:
            reported_multiple_uuids_for_office.append(uuid)
        return True
    else:
        return False


def office_uuid_has_multiple_names(uuid):
    if counts_by_office_uuid[uuid]['Office Name'] > 1 and \
       uuid not in reported_multiple_office_names_uuids:
        reported_multiple_office_names_uuids.append(uuid)
        return True
    else:
        return False


def office_uuid_has_multiple_bodies(uuid):
    if counts_by_office_uuid[uuid]['Body Name'] > 1 and \
       uuid not in reported_multiple_body_names_uuids:
        reported_multiple_body_names_uuids.append(uuid)
        return True
    else:
        return False


def office_uuid_has_multiple_categories(uuid):
    if counts_by_office_uuid[uuid]['Office Category'] > 1 and \
       uuid not in reported_multiple_categories_uuids:
        reported_multiple_categories_uuids.append(uuid)
        return True
    else:
        return False


def office_uuid_has_multiple_levels(uuid):
    if counts_by_office_uuid[uuid]['Office Level'] > 1 and \
       uuid not in reported_multiple_levels_uuids:
        reported_multiple_levels_uuids.append(uuid)
        return True
    else:
        return False


def office_uuid_has_multiple_roles(uuid):
    if counts_by_office_uuid[uuid]['Office Role'] > 1 and \
       uuid not in reported_multiple_roles_uuids:
        reported_multiple_roles_uuids.append(uuid)
        return True
    else:
        return False


def is_dupe_candidate(candidate_name):

    simplified_name = simplify_name(candidate_name)

    if simplified_name in reported_dupe_candidates or \
       simplified_name not in suspected_dupe_candidates:
        return False

    rows_with_candidate = [str([row['Office Name'],
                                row['State'],
                                simplify_district(row['Electoral District']),
                                row['Office Name'],
                                (row['Official Party'] if
                                 row['State'] == 'NY' else '')])
                           for row in csv_rows if
                           row['Simplified Name'] == simplified_name]

    distinct_offices = list(set(rows_with_candidate))
    is_dupe = len(rows_with_candidate) > len(distinct_offices)

    if is_dupe:
        reported_dupe_candidates.append(simplified_name)

    return is_dupe


def is_office_name_variant_spelling(office_name):
    bare_office_name = bare_string(office_name)

    return 'court ' in bare_office_name and \
        bare_office_name.replace('court ', '') in office_names


def is_dupe_uuid(uuid):
    is_dupe = uuid in dupe_uuids and uuid not in reported_dupe_uuids

    if is_dupe:
        reported_dupe_uuids.append(uuid)

    return is_dupe


def is_dupe_internal_id(internal_id):
    is_dupe = internal_id in dupe_internal_ids and \
              internal_id not in reported_dupe_internal_ids

    if is_dupe:
        reported_dupe_internal_ids.append(internal_id)

    return is_dupe


def office_name_describes_person(office_name):
    body_terms = ['senate', 'house', 'commission', 'board', 'council',
                  'committee', 'board of education', 'assembly',
                  'representatives']
    exceptions = ['Delegate to the U.S. House of Representatives']

    return not any([bare_string(office_name).endswith(term) for
                    term in body_terms]) or office_name in exceptions


def gov_body_describes_body(gov_body):
    person_terms = ['member', 'trustee', 'president', 'commissioner',
                    'person', 'director', 'chairperson', 'alderman',
                    'councillor', 'councilman', 'senator']

    return not any([bare_string(gov_body).endswith(term) for
                    term in person_terms])


def name_has_repeated_term(name):
    simplified_name = bare_string(name)
    terms = simplified_name.split(' ') + ['school district']
    dupes = [term for term in terms if
             term not in ['walla', 'paw'] and
             re.search(r'\b{} {}\b'.format(term, term), simplified_name) and
             not re.search(r'\b{} {}$'.format(term.title(), term), name)]

    return len(dupes) > 0


def district_has_something_of(district_name):
    simplified_name = bare_string(district_name)
    return re.match('^(?:city|village|township|town|county) of ',
                    simplified_name)


def phone_number_is_valid(string):
    try:
        is_valid = phonenumbers.is_valid_number(
            phonenumbers.parse(
                re.sub('\D', '', string),
                'US'
            )
        )
    except phonenumbers.phonenumberutil.NumberParseException:
        is_valid = False

    return is_valid


def has_illegal_chars(string):
    bad_ascii_chars = list(';_<>')
    has_bad_ascii_chars = any((lambda bad_char: bad_char in string)(char) for
                              char in bad_ascii_chars)
    try:
        if not has_bad_ascii_chars and unidecode(unicode(string)):
            return False
        else:
            return True
    except:
        return True


def email_is_well_formed(email):
    return validate_email(email) and \
        not has_illegal_chars(email.replace('_', ''))


def district_is_misspelled(district):
    words = district.split(' ')
    ratios = [SequenceMatcher(
        lambda x: x == ' ', 'district', re.sub(r'\W', '', word.lower())
    ).ratio() for word in words if word not in ['Subdistrict']]

    return any([ratio > 0.85 and ratio < 1.00 for ratio in ratios])

office_levels = ['international', 'country', 'administrativeArea1', 'regional',
                 'administrativeArea2', 'locality', 'subLocality1',
                 'subLocality2', 'special']

office_roles = ['headOfState', 'headOfGovernment', 'deputyHeadOfGovernment',
                'governmentOfficer', 'executiveCouncil', 'legislatorUpperBody',
                'legislatorLowerBody', 'highestCourtJudge', 'judge',
                'schoolBoard', 'specialPurposeOfficer']

uri_pattern = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
    r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)


def uri_is_well_formed(uri):
    if not uri.lower().startswith('http'):
        uri = 'http://' + uri

    return bool(uri_pattern.match(uri))

uuid_pattern = re.compile(
    r'^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$'
)

ocdid_pattern = re.compile(
    r'ocd-division/country:us(?:/(?:state|district):[a-z]{2}(?:/[-\w:/~]+)?)?'
)

validators = {
    'Person UUID': [
        # {'check': lambda val: val == '' or bool(uuid_pattern.match(val)),
        #  'error': 'Malformed UUID'},
        {'check': lambda val: not is_dupe_uuid(val),
         'error': 'Candidate UUID is duplicated'}
    ],
    'UID': [
        # {'check': lambda val: val == '' or bool(uuid_pattern.match(val)),
        #  'error': 'Malformed Office UUID'},
        {'check': lambda val: (val == '' or
                               not office_uuid_has_multiple_names(val)),
         'error': 'Multiple office names found for single office UUID'},
        {'check': lambda val: (val == '' or
                               not office_uuid_has_multiple_bodies(val)),
         'error': 'Multiple body names found for single office UUID'},
        {'check': lambda val: (val == '' or
                               not office_uuid_has_multiple_categories(val)),
         'error': 'Multiple categories found for single office UUID'},
        {'check': lambda val: (val == '' or
                               not office_uuid_has_multiple_levels(val)),
         'error': 'Multiple levels found for single office UUID'},
        {'check': lambda val: (val == '' or
                               not office_uuid_has_multiple_roles(val)),
         'error': 'Multiple roles found for single office UUID'}
    ],
    'State': [
        {'check': lambda val: bool(re.match('^[A-Z]{2}$', val)),
         'error': 'State must be two capital letters'}
    ],
    'Office Level': [
        {'check': lambda val: val in office_levels,
         'error': 'Office level is invalid'}
    ],
    'Office Role': [
        {'check': lambda val: val in office_roles,
         'error': 'Office role is invalid'}
    ],
    'Electoral District': [
        {'check': lambda val: val != '',
         'error': 'Office must have an electoral district'},
        {'check': lambda val: not name_has_repeated_term(val),
         'error': 'Electoral district has a repeated term'},
        {'check': lambda val: not district_has_something_of(val),
         'error': 'Electoral district starts with "(City, Town, etc.) of"'},
        {'check': lambda val: not re.search(' borough township', val,
                                            flags=re.IGNORECASE),
         'error': 'Electoral district has "borough township"'},
        {'check': lambda val: not district_is_misspelled(val),
         'error': 'Electoral district has a misspelling of "District"'}
    ],
    'Office Category': [
        {'check': lambda val: val.strip() != '',
         'error': 'Office must have a category'},
    ],
    'Office Name': [
        {'check': lambda val: not has_illegal_chars(val),
         'error': 'Office name has illegal characters'},
        {'check': lambda val: val != '',
         'error': 'Office must have a name'},
        {'check': lambda val: office_name_describes_person(val),
         'error': 'Office name describes a government body'},
        {'check': lambda val: not name_has_repeated_term(val),
         'error': 'Office name has a repeated term'},
        {'check': lambda val: not re.search(' borough township', val,
                                            flags=re.IGNORECASE),
         'error': 'Office name has "borough township"'},
        {'check': lambda val: not district_is_misspelled(val),
         'error': 'Office name has a misspelling of "District"'},
        # {'check': lambda val: not is_office_name_variant_spelling(val),
        #  'error': 'Office name is duplicated with spelling variation'}

    ],
    'Official Name': [
        {'check': lambda val: not has_illegal_chars(val),
         'error': 'Official name has illegal characters'},
        {'check': lambda val: val != val.upper(),
         'error': 'Official name is in all caps'},
        {'check': lambda val: not is_dupe_candidate(val),
         'error': 'Official is duplicated'}
    ],
    'Body Name': [
        {'check': lambda val: val == '' or gov_body_describes_body(val),
         'error': 'Government body describes a person'},
        {'check': lambda val: not name_has_repeated_term(val),
         'error': 'Government body has a repeated term'}
    ],
    'Phone': [
        {'check': lambda val: val == '' or phone_number_is_valid(val),
         'error': 'Phone number is malformed'}
    ],
    'Website': [
        {'check': lambda val: val == '' or uri_is_well_formed(val),
         'error': 'Website is malformed'}
    ],
    'Email': [
        {'check': lambda val: val == '' or email_is_well_formed(val),
         'error': 'Email is malformed'}
    ],
    'Mailing Address': [
        {'check': lambda val: val == '' or not has_illegal_chars(val),
         'error': 'Mailing address has illegal characters'}
    ],
    'Facebook URL': [
        {'check': lambda val: val == '' or uri_is_well_formed(val),
         'error': 'Facebook URL is malformed'}
    ],
    'Twitter Name': [
        {'check': lambda val: val == '' or re.match(r'^\w+$', val),
         'error': 'Twitter Name is malformed'}
    ],
    'Google Plus URL': [
        {'check': lambda val: val == '' or uri_is_well_formed(val),
         'error': 'Google Plus URL is malformed'}
    ],
    'Wiki Word': [
        {'check': lambda val: val == '' or re.match(r'^[-.,()\'\w]+$', val),
         'error': 'Wiki Word is malformed'}
    ],
    'Youtube': [
        {'check': lambda val: val == '' or uri_is_well_formed(val),
         'error': 'Youtube is malformed'}
    ],
    'ocdid': [
        {'check': lambda val: val == '' or ocdid_pattern.match(val),
         'error': 'OCDID is malformed'}
    ]
}

last_state = None
reported_missing_columns = []


def validate_row(i, row):
    global last_state
    state = row['State'] or last_state

    # Missing columns
    errors = {'row': i + 2, 'errors': []}

    columns = ['Person UUID', 'State', 'Office Level', 'Office Role',
               'Electoral District', 'Body Name', 'Office Category',
               'Office Name', 'Office Base', 'Official Name',
               'Official Party', 'Incumbent', 'Phone', 'Mailing Address',
               'Website', 'Email', 'Facebook URL', 'Twitter Name',
               'Google Plus URL', 'Wiki Word', 'Youtube', 'source', 'OCDID',
               'UID']

    for column in columns:
        if column not in row and \
           column not in reported_missing_columns:
            errors['errors'].append({'message': 'Missing column: ' + column})
            reported_missing_columns.append(column)
        elif column in row:
            value = row[column].strip()
            for error in validate_cell(column, value):
                errors['errors'].append({'message': error,
                                         'value': row[column]})

    office = office_string(row)
    if office_has_multiple_uuids(office):
        uuids = uuids_by_office[office]
        errors['errors'].append({
            'message': 'Office has multiple UUIDs',
            'value': '{} ({})'.format(row['Office Name'],
                                      (', '.join(uuids)).strip())
        })

    # Missing office UUID for present candidate UUID
    if row['Person UUID'] != '' and row['UID'] == '':
        errors['errors'].append({
            'message': 'Empty office UUID with non-empty candidate UUID',
            'value': row['Person UUID']
        })
        reported_candidate_uuids_with_no_office_uuids.append(row['Person UUID'])

    last_state = state
    return errors


def validate_cell(column, value):
    if column not in validators.keys():
        return []

    errors = filter(None, [None if validator['check'](value) else
                           validator['error'] for validator in
                           validators[column]])

    return errors

errors = [validate_row(i, row) for i, row in enumerate(csv_rows) if
          row['Official Name'] != '']
errors = list(k for k, _ in itertools.groupby(
    error for error in sorted(errors) if error['errors'] != []))
errors.sort(key=lambda error: error['row'])


if len(errors) > 0:
    print csv_file.name + ' has errors'

    for error in errors:
        pprint(error)
        print


else:
    print csv_file.name + ' validates'
