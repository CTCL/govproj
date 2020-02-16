class Conn(object):
    USER = ''
    PW = ''
    HOST = ''
    DB = ''

class Database(object):
    ENUMS = {'ocdid_type':('political','geographic','precinct'),
            'ocdid_level':('country','state','county','municipal')}
    TABLES = {'ocdid':"""id TEXT PRIMARY KEY,
                            name TEXT,
                            type ocdid_type,
                            level ocdid_level,
                            jurisdiction_type_1 TEXT,
                            jurisdiction_value_1 TEXT,
                            jurisdiction_type_2 TEXT,
                            jurisdiction_value_2 TEXT,
                            jurisdiction_type_3 TEXT,
                            jurisdiction_value_3 TEXT,
                            jurisdiction_type_4 TEXT,
                            jurisdiction_value_4 TEXT,
                            jurisdiction_type_5 TEXT,
                            jurisdiction_value_5 TEXT,
                            jurisdiction_type_6 TEXT,
                            jurisdiction_value_6 TEXT,
                            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_current BOOLEAN,
                            is_exception BOOLEAN,
                            ocdid TEXT REFERENCES ocdid(id)""",
                'electoral_district':"""id TEXT PRIMARY KEY,
                                        name TEXT,
                                        type TEXT,
                                        state_key TEXT,
                                        updated TIMESTAMP,
                                        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        ocdid TEXT""",
                'office':"""id TEXT PRIMARY KEY,
                                name TEXT,
                                office_level TEXT,
                                body_name TEXT,
                                state_key TEXT,
                                state TEXT,
                                body_represents_state TEXT,
                                updated TIMESTAMP,
                                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                electoral_district_name TEXT,
                                electoral_district_id TEXT REFERENCES electoral_district(id)""",
                'office_holder':"""id TEXT PRIMARY KEY,
                                    identifier TEXT,
                                    name TEXT,
                                    mailing_address TEXT,
                                    state_key TEXT,
                                    website TEXT,
                                    email TEXT,
                                    phone TEXT,
                                    twitter_name TEXT,
                                    facebook_url TEXT,
                                    youtube TEXT,
                                    wiki_word TEXT,
                                    party TEXT,
                                    birth_year TEXT,
                                    birth_month TEXT,
                                    birth_day TEXT,
                                    dob TEXT,
                                    election_year TEXT,
                                    expiration_date TEXT,
                                    updated TIMESTAMP,
                                    date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP""",
                'office_holder_to_office':"""office_holder_id TEXT REFERENCES office_holder(id),
                                            office_id TEXT REFERENCES office(id),
                                            state_key TEXT,
                                            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP"""}

class Sql(object):
    DROP_ENUM = 'DROP TYPE IF EXISTS {} CASCADE'
    CREATE_ENUM = 'CREATE TYPE {} AS ENUM {}'
    DROP_TABLE = 'DROP TABLE IF EXISTS {} CASCADE'
    CREATE_TABLE = 'CREATE TABLE {} ({})'
    COPY_IMPORT = "COPY {}({}) FROM '{}' WITH CSV HEADER"
    COPY_EXPORT = "COPY ({}) TO '{}dump.csv' CSV DELIMITER ','"

class District(object):
    LEVELS = {'country':'country',
                'state':'state',
                'county':'county',
                'district':'municipal',
                'place':'municipal'}
    TYPES = ['ward','school','precinct',
                    'council','park','commission',
                    'house','assembly','senate',
                    'district']
    SPLIT_TYPES = ['precinct','district','ward']
    ALT_COUNTIES = {'la':'parish','ak':'borough'}
    TYPE_CONVERSIONS = {
                'city':set(['place','district']),
                'town':set(['place']),
                'township':set(['place']),
                'village':set(['place']),
                'county':set(['county','parish','census_area','borough','region']),
                'parish':set(['county','parish','census_area','borough','region']),
                'census_area':set(['county','parish','census_area','borough','region']),
                'borough':set(['county','parish','census_area','borough','region']),
                'region':set(['county','parish','census_area','borough','region']),
                'state':set(['state','territory','district']),
                'territory':set(['state','territory','district']),
                'council':set(['council_district','commissioner_district']),
                'commissioner':set(['council_district','commissioner_district']),
                'court':set(['chancery_court','superior_court','supreme_court','court_of_appeals','district_court','circuit_court','constable_districts']),
                'school':set(['school_board']),
                'ward':set(['anc','ward','precinct']),
                'anc':set(['anc','ward','precinct']),
                'precinct':set(['anc','ward','precinct']),
                'country':set(['country']),
                'cd':set(['cd']),
                'sldl':set(['sldl']),
                'sldu':set(['sldu'])}

class Output(object):
    DIR = '/tmp/govproj/'

class Ocdid(object):
    NOT_CURRENT = 'not_current_districts.csv'
    EXCEPTIONS = 'ocdid_exceptions.csv'
    OCDID = 'ocdid.csv'
    FIELDS = ['id','name','type','level',
                'jurisdiction_type_1','jurisdiction_value_1',
                'jurisdiction_type_2','jurisdiction_value_2',
                'jurisdiction_type_3','jurisdiction_value_3',
                'jurisdiction_type_4','jurisdiction_value_4',
                'jurisdiction_type_5','jurisdiction_value_5',
                'jurisdiction_type_6','jurisdiction_value_6',
                'date_created','is_current','is_exception','ocdid']
    OCDID_FILES = {OCDID:FIELDS}
    OCDID_DATA = Output.DIR + 'dump.csv'
    EXPORT_QUERY = 'SELECT id, ocdid FROM ocdid WHERE is_current IS TRUE'
    PREFIX = 'ocd-division/country:us/'

class Match(object):
    RATIO = 90
    LIMIT = 10

class OfficeHolder(object):
    DIR = '/home/jensen/Dropbox/Projects/noBIP/social_media_collection/office_holders/'
    OPTIONAL_OFF = {'Body Represents - County':'body_represents_county',
                    'Body Represents - Muni':'body_represents_muni',
                    'Source':'source'}
    OPTIONAL_OH = {'Source':'source',
                    'Official Party':'party',
                    'Phone':'phone',
                    'Mailing Address':'mailing_address',
                    'Wiki Word':'wiki_word',
                    'Youtube':'youtube',
                    'DOB':'dob'}
    OFFICE_HOLDER_FILES = {'electoral_district.csv':['id','name','type','state_key','updated','ocdid'],
                            'office.csv':['id','name','office_level','body_name','state_key','state','body_represents_state','updated','electoral_district_name','electoral_district_id'],
                            'office_holder.csv':['id','identifier','name','mailing_address','state_key','website','email','phone','twitter_name','facebook_url','youtube','wiki_word','party','birth_year','birth_month','birth_day','dob','election_year','expiration_date','updated'],
                            'office_holder_to_office.csv':['office_holder_id','office_id','state_key']}
