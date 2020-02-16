import psycopg2
import sys
import stat
from os import walk, path, makedirs, unlink, chmod, listdir
from shutil import rmtree
import csv
import hashlib
import re
from datetime import datetime
from csv import DictReader,DictWriter
from argparse import ArgumentParser
from config import Conn,Database,Sql,District,Output,Ocdid,OfficeHolder,Match

date_val = str(datetime.now())
date_val = date_val[:date_val.find('.')]
conn = psycopg2.connect(host=Conn.HOST,database=Conn.DB,
                        user=Conn.USER,password=Conn.PW)
cur = conn.cursor()

def create_db():
    for k,v in Database.ENUMS.iteritems():
        cur.execute(Sql.DROP_ENUM.format(k))    
        cur.execute(Sql.CREATE_ENUM.format(k,v))    
    for k,v in Database.TABLES.iteritems():
        cur.execute(Sql.DROP_TABLE.format(k))    
        cur.execute(Sql.CREATE_TABLE.format(k,v))    
    conn.commit()

def load_data(files,data):
    for f,fields in files.iteritems():
        name = f[:f.find('.csv')]
        with open(Output.DIR + f,'w') as w:
            writer = DictWriter(w,fieldnames=fields,extrasaction='ignore')
            writer.writeheader()
            for k,v in data[name].iteritems():
                writer.writerow(v)
        cur.copy_expert(Sql.COPY_IMPORT.format(name,','.join(fields),Output.DIR+f), sys.stdin)
        conn.commit()

def export_data(query):
    cur.copy_expert(Sql.COPY_EXPORT.format(query,Output.DIR),sys.stdout)
    conn.commit()

def parse_ocdid(ocdid):
    juris_count = 0
    parsed_ocdid = {}

    for section in ocdid.split('/')[1:]: 
        juris_count += 1
        t,v = section.split(':')
        parsed_ocdid['jurisdiction_type_{}'.format(juris_count)] = t
        parsed_ocdid['jurisdiction_value_{}'.format(juris_count)] = v

    last_type = parsed_ocdid['jurisdiction_type_{}'.format(juris_count)]
    if last_type in District.LEVELS.keys():
        parsed_ocdid['type'] = 'geographic'
        parsed_ocdid['level'] = District.LEVELS[last_type]
        return parsed_ocdid
    elif last_type == 'precinct':
        parsed_ocdid['type'] = 'precinct'
    else:
        parsed_ocdid['type'] = 'political'

    while juris_count > 0:
        juris_count -= 1
        juris_type = parsed_ocdid['jurisdiction_type_{}'.format(juris_count)]
        if juris_type in District.LEVELS:
            parsed_ocdid['level'] = District.LEVELS[juris_type]
            return parsed_ocdid

    return parsed_ocdid

def get_ocdids():
    not_current = set()
    data = {}

    with open(Ocdid.NOT_CURRENT,'r') as f:
        for row in f:
            not_current.add(row.strip())

    for f in [Ocdid.OCDID,Ocdid.EXCEPTIONS]:
        with open(f,'r') as r:
            reader = csv.reader(r)
            for row in reader:
                if not row:
                    continue
                id_val = row[0]

                if f == Ocdid.EXCEPTIONS:
                    # skip unnecessary districts
                    if row[2].startswith('Doesn\'t exist') or row[0][:row[0].rfind(':')] != row[1][:row[0].rfind(':')]:
                        continue
                    data[id_val] = {'id':id_val,
                                        'name':row[2],
                                        'is_exception':1,
                                        'ocdid':row[1]}
                else:
                    data[id_val] = {'id':id_val,
                                        'name':row[1],
                                        'is_exception':0}

                data[id_val].update(parse_ocdid(id_val))
                if id_val in not_current:
                    data[id_val]['is_current'] = 0
                else:
                    data[id_val]['is_current'] = 1
    return data

def clear_dir():
    if not path.exists(Output.DIR):
        makedirs(Output.DIR)
    chmod(Output.DIR,stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO)
    for root,dirs,files in walk(Output.DIR):
        for f in files:
            unlink(path.join(root,f))
        for d in dirs:
            rmtree(path.join(root,d))

def is_exact(prefix_list):
    test_id = Ocdid.PREFIX + '/'.join(prefix_list)
    if ocdid.is_ocdid(test_id):
        return test_id
    return None

def match_exists(prefix_list,offset):
    new_prefix = is_exact(prefix_list[:offset])
    if new_prefix:
        dist_type,dist_name = prefix_list[offset].split(':')
        return ocdid.match_name(new_prefix,dist_type,dist_name)
    return None,-1
    
def get_full_prefix(prefix_list):

    # NY City/Village Exception
    if prefix_list[-1].startswith('place:city_of_') or prefix_list[-1].startswith('place:village_of_'):
        prefix_list.pop(-2)
        prefix_list[-1] = prefix_list[-1].replace('city_of_','')
        prefix_list[-1] = prefix_list[-1].replace('village_of_','')

    id_val = is_exact(prefix_list)
    if id_val:
        return id_val,100
   
    if len(prefix_list) > 1: 
        id_val,ratio = match_exists(prefix_list,-1)
        if ratio >= Match.RATIO:
            return id_val,ratio

    if len(prefix_list) > 2:
        id_val,ratio = match_exists(prefix_list,-2)
        if ratio <= Match.RATIO:
            return None,-1
        prefix_list[-2] = id_val.split('/')[-1]
        
        id_val = is_exact(prefix_list)
        if id_val:
            return id_val,100

        id_val,ratio = match_exists(prefix_list,-1)
        if ratio >= Match.RATIO:
            return id_val,ratio 
        else:
            prefix_list.pop(-2)
            id_val = is_exact(prefix_list)
            if id_val:
                return id_val,100
            id_val,ratio = match_exists(prefix_list,-1)
            if ratio >= Match.RATIO:
                return id_val,ratio
    return None,-1

def is_sub_district(e_district,prefix_list):
    if 'precinct ' in e_district or 'district ' in e_district:
        return True
    elif ' ward ' in e_district or (e_district.startswith('ward ') and len(e_district) < 9):
        return True
    else:
        return False

def get_sub_district(e_district,prefix_list):
    for t in District.TYPES:
        if t in e_district:
            if t == 'house' or t == 'assembly':
                dist_type = 'sldl'
            elif t == 'senate':
                dist_type = 'sldu'
            else:
                dist_type = t
            break
    for s in District.SPLIT_TYPES:
        if s in e_district:
            return dist_type,e_district.split(s)[-1].strip().replace(' ','_')

def assign_ocdids():
    oh_data = []
    for f in listdir(OfficeHolder.DIR):
        print f
        with open(OfficeHolder.DIR + f,'rU') as r:
            reader = DictReader(r)

            ocdid_vals = {}
            unmatched = {}

            for row in reader:
                state = row['Body Represents - State'].lower().replace(' ','_')
                county = row['Body Represents - County'].lower().replace(' ','_')
                muni = row['Body Represents - Muni'].lower().replace(' ','_')
                ed = row['Electoral District'].lower()

                prefix_list = []
                if state: 
                    prefix_list.append('state:{}'.format(state))
                if county:
                    if state in District.ALT_COUNTIES:
                        prefix_list.append('{}:{}'.format(District.ALT_COUNTIES[state],county))
                    else:
                        if state == 'nh' and county.startswith('co'):
                            county = 'coos'
                        prefix_list.append('county:{}'.format(county))
                if muni:
                    if muni == 'dc':
                        prefix_list.append('district:{}'.format(muni))
                    else:
                        prefix_list.append('place:{}'.format(muni))

                ocdid_key = tuple(prefix_list)
                if ocdid_key in ocdid_vals:
                    full_prefix,ratio = ocdid_vals[ocdid_key]['ocdid'],ocdid_vals[ocdid_key]['ratio']
                else:
    #                print prefix_list
                    full_prefix,ratio = get_full_prefix(prefix_list)
                    ocdid_vals[ocdid_key] = {'ocdid':full_prefix,'ratio':ratio}

                if is_sub_district(ed,prefix_list):
                    d_type,d_name = get_sub_district(ed,prefix_list)
                    unmatched_key = u'{}:{}'.format(full_prefix,d_type)
                    if unmatched_key not in unmatched:
                        unmatched[unmatched_key] = {'prefix':full_prefix,'districts':{},'dist_type':d_type}
                    if d_name not in unmatched[unmatched_key]['districts']:
                        unmatched[unmatched_key]['districts'][d_name] = []
                    unmatched[unmatched_key]['districts'][d_name].append(row)
                else:
                    if full_prefix == None:
                        full_prefix = ''
                    row['match_ratio'] = ratio
                    row['ocdid'] = full_prefix
                    oh_data.append(row)

            for k,v in unmatched.iteritems():
                full_prefix = v['prefix']
                d_type = v['dist_type']
                districts = v['districts']

                type_val = ocdid.match_type(full_prefix,d_type,len(districts))
                if not type_val:
                    for d_name,rows in districts.iteritems():
                        for row in rows:
                            row['match_ratio'] = -1
                            row['ocdid'] = ''
                            oh_data.append(row)
                else:
                    for d_name,rows in districts.iteritems():
                        id_val,ratio = ocdid.match_name(full_prefix,type_val,d_name) #If ratio fails here :(
                        if id_val == None:
                            id_val = ''
                        for row in rows:
                            row['match_ratio'] = ratio
                            row['ocdid'] = id_val
                            oh_data.append(row)
    return oh_data

def split_data(oh_data):
    split_data = {'office_holder':{},'office':{},'electoral_district':{},'office_holder_to_office':{}}
    count = 0
    for row in oh_data:
        count += 1
        if not row['ocdid']:
            row['ocdid'] = row['UID']
        ed_id = row['ocdid'].replace('ocd-division','ed')
        off_part = re.sub('[^0-9a-zA-Z]+','_',row['Office Name'])
        off_id = '{}/{}'.format(row['ocdid'].replace('ocd-division','office'),off_part)
        oh_id = '{}/{}/{}'.format(row['ocdid'].replace('ocd-division','office_holder'),off_part,hashlib.md5(row['Official Name']).hexdigest())
        
        if ed_id not in split_data['electoral_district']:
            ed = row['Electoral District'].replace('-','_').replace(' ','_').lower()+'_'+row['Body Represents - State']
            ocd_id = row['ocdid']
            type_val = ocd_id[ocd_id.rfind('/')+1:ocd_id.rfind(':')]
            split_data['electoral_district'][ed_id] = {'updated':date_val,
                                                        'name':row['Electoral District'],
                                                        'state_key':row['Body Represents - State'],
                                                        'type':type_val,
                                                        'ocdid':ocd_id,
                                                        'id':ed_id}
        if off_id not in split_data['office']:
            office_data = {'updated':date_val,
                            'electoral_district_id':ed_id,
                            'name':row['Office Name'],
                            'office_level':row['Office Level'],
                            'state_key':row['Body Represents - State'],
                            'body_name':row['Body Name'],
                            'state':row['State'],
                            'electoral_district_name':row['Electoral District'],
                            'body_represents_state':row['Body Represents - State'],
                            'id':off_id}
            for k,v in OfficeHolder.OPTIONAL_OFF.iteritems():
                if len(row[k]) > 0:
                    office_data[v] = row[k] 
            split_data['office'][off_id] = office_data

        split_data['office_holder_to_office'][count] = {'office_holder_id':oh_id,
                                                        'state_key':row['Body Represents - State'],
                                                        'office_id':off_id}
        office_holder_data = {'website':row['Website'],
                                'updated':date_val,
                                'name':row['Official Name'],
                                'mailing_address':row['Mailing Address'],
                                'facebook_url':row['Facebook URL'],
                                'state_key':row['Body Represents - State'],
                                'email':row['Email'],
                                'phone':row['Phone'],
                                'youtube':row['Youtube'],
                                'wiki_word':row['Wiki Word'],
                                'twitter_name':row['Twitter Name'],
                                'party':row['Official Party'],
                                'birth_year':row['Birth Year'],
                                'birth_month':row['Birth Month'],
                                'birth_day':row['Birth Day'],
                                'dob':row['DOB'],
                                'election_year':row['Election Year'],
                                'expiration_date':row['Expires'],
                                'identifier':row['UID'],
                                'id':oh_id}
        for k,v in OfficeHolder.OPTIONAL_OH.iteritems():
            if len(row[k]) > 0:
                office_data[v] = row[k] 
        split_data['office_holder'][count] = office_holder_data
    return split_data

def main():
    usage='Setup the database and populate with data'
    description='Accepts a series of files to load to the database and match'
    parser = ArgumentParser(usage=usage, description=description)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--db', action='store_true')
    parser.add_argument('--ocdid', action='store_true')
    parser.add_argument('--office', action='store_true')

    args = parser.parse_args()
    if not (args.all or args.db or args.ocdid or args.office):
        args.all = True

    if args.all or args.db:
        create_db()
    if args.all or args.ocdid:
        clear_dir()
        ocdid_data = {'ocdid':get_ocdids()}
        load_data(Ocdid.OCDID_FILES,ocdid_data)
    if args.all or args.office:
        clear_dir()
        export_data(Ocdid.EXPORT_QUERY)
        global ocdid
        import ocdid
        oh_data = assign_ocdids()
        office_holder_data = split_data(oh_data)
        load_data(OfficeHolder.OFFICE_HOLDER_FILES,office_holder_data)
    
if __name__ == '__main__':
    main()
