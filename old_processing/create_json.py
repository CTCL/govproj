from csv import DictReader
from process_config import Dirs, NewJson
import os
import re
import hashlib
import json

"""
Very basic script to convert the flat file formatted data into Google
  formatted json. Data is written out to the production/json directory
  and a folder for the different json versions.

Requirements:
    Python2.7
    config data

Constants:
    Dirs.PROD_FF -- directory for production flat files
    Dirs.PROD_JSON -- directory for production json
    Dirs.JSON_VERSION -- directory for different dated jsons
    NewJson.OPTIONAL_OFF -- optional office fields
    NewJson.OPTIONAL_OH -- options office holder fields
"""

dist_counter = 0
districts = {}
office_counter = 0
offices = {}
office_holder_to_office = []
office_holder = []
districts_final = []
offices_final = []

# Load the production flat files directory, convert each file to json format
for f in os.listdir(Dirs.PROD_FF):

    if f.startswith('.') or f.startswith('unverified'):
        continue

    with open(Dirs.PROD_FF+f, 'rU') as r:
        print f
        reader = DictReader(r)

        for row in reader:
            # Setup the id's for each json type. Each id is very similar to
            # ocdids, the difference is what replaces 'ocd-division': 'ed',
            # 'office', and 'office_holder'
            ed_id = row['OCDID'].replace('ocd-division', 'ed')
            off_part = re.sub('[^0-9a-zA-Z]+', '_', row['Office Name'])
            off_id = '{}/{}'.format(row['OCDID'].replace('ocd-division',
                                                         'office'),
                                    off_part)
            oh_id = '{}/{}/{}'.format(row['OCDID'].replace('ocd-division',
                                                           'office_holder'),
                                      off_part,
                                      hashlib.md5(row['Official Name']).hexdigest())

            # Only convert unique electoral districts
            if ed_id not in districts:
                ed = '{}_{}'.format(row['Electoral District'].replace('-', '_').replace(' ', '_').lower(),
                                    row['Body Represents - State'])
                dist_counter += 1
                ocd_id = row['OCDID']
                type_val = ocd_id[ocd_id.rfind('/')+1:ocd_id.rfind(':')]
                districts[ed_id] = {'election_key': '2014',
                                    'updated': Dirs.DATE_VAL,
                                    'name': row['Electoral District'],
                                    'state_key': row['Body Represents - State'],
                                    'source': 'office_holders_data',
                                    'identifier': '{0}_{1}'.format(ed, type_val),
                                    'type': type_val,
                                    'ocdid': ocd_id,
                                    'id': ed_id}
            # Only convert unique offices
            if off_id not in offices:
                office_counter += 1
                office_data = {'election_key': '2014',
                               'updated': Dirs.DATE_VAL,
                               'electoral_district_id': ed_id,
                               'name': row['Office Name'],
                               'electoral_district_type': '',
                               'office_level': row['Office Level'],
                               'state_key': row['Body Represents - State'],
                               'body_name': row['Body Name'],
                               'state': row['State'],
                               'electoral_district_name': row['Electoral District'],
                               'body_represents_state': row['Body Represents - State'],
                               'identifier': '{0}_{1}'.format(row['Electoral District'], row['Office Name']),
                               'id': off_id}
                # Optional fields for office only added if they have content
                for k, v in NewJson.OPTIONAL_OFF.iteritems():
                    if len(row[k]) > 0:
                        office_data[v] = row[k]
                offices[off_id] = office_data
            # For each row, add the office holder and the office holder
            # to office connection
            office_holder_to_office.append({'election_key': '2014',
                                            'office_holder_id': oh_id,
                                            'state_key': row['Body Represents - State'],
                                            'office_id': off_id})
            office_holder_data = {'website': row['Website'],
                                  'election_key': '2014',
                                  'updated': Dirs.DATE_VAL,
                                  'name': row['Official Name'],
                                  'mailing_address': row['Mailing Address'],
                                  'facebook_url': row['Facebook URL'],
                                  'state_key': row['Body Represents - State'],
                                  'email': row['Email'],
                                  'phone': row['Phone'],
                                  'google_plus_url': row['Google Plus URL'],
                                  'twitter_name': row['Twitter Name'],
                                  'party': row['Official Party'],
                                  'identifier': row['UID'],
                                  'id': oh_id}
            # Optional fields for office holder only added if they have content
            for k, v in NewJson.OPTIONAL_OH.iteritems():
                if len(row[k]) > 0:
                    office_data[v] = row[k]
            office_holder.append(office_holder_data)

# Convert districts and offices from dictionaries to lists. Don't know
# why I just didn't use dictionary comprehensions.
for k, v in districts.iteritems():
    districts_final.append(v)
for k, v in offices.iteritems():
    offices_final.append(v)

print 'District Count: {}'.format(len(districts_final))
print 'Office Count: {}'.format(len(offices_final))
print 'Office Holder to Office Count: {}'.format(len(office_holder_to_office))
print 'Officer Holder Count: {}'.format(len(office_holder))

if not os.path.exists(Dirs.JSON_VERSION):
    os.mkdir(Dirs.JSON_VERSION)

for d in [Dirs.JSON_VERSION, Dirs.PROD_JSON]:
    with open(d+'electoral_district.json', 'w') as w:
        w.write(json.dumps(districts_final))
    with open(d+'office.json', 'w') as w:
        w.write(json.dumps(offices_final))
    with open(d+'office_holder_to_office.json', 'w') as w:
        w.write(json.dumps(office_holder_to_office))
    with open(d+'office_holder.json', 'w') as w:
        w.write(json.dumps(office_holder))
