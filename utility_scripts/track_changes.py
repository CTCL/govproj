import json
from csv import DictWriter

JSON_DIR = '../json/{}/'
ED_FIELDS = ['name','ocdid','identifier','type','state_key']
ED_CHANGE_FIELDS = ['id','name_old','name_new','ocdid_old','ocdid_new','identifier_old','identifier_new','type_old','type_new','state_key_old','state_key_new']
OFF_FIELDS = ['electoral_district_id','electoral_district_name','name','identifier','state_key','office_level','body_name']
OFF_CHANGE_FIELDS = ['id','electoral_district_id_old','electoral_district_id_new','electoral_district_name_old','electoral_district_name_new','name_old','name_new','identifier_old','identifier_new','state_key_old','state_key_new','office_level_old','office_level_new','body_name_old','body_name_new']
OH_FIELDS = ['name','id']
OH_CHANGE_FIELDS = ['identifier','name_old','name_new','id_old','id_new']
old_version = '2013-11-14'
new_version = '2013-11-22'

old_ed = {}
new_ed = {}
old_off = {}
new_off = {}
old_oh = {}
new_oh = {}

with open(JSON_DIR.format(old_version)+'electoral_district.json') as r:
    data = json.load(r)
    for ed in data:
        old_ed[ed['id']] = ed
with open(JSON_DIR.format(new_version)+'electoral_district.json') as r:
    data = json.load(r)
    for ed in data:
        new_ed[ed['id']] = ed

new_districts = []
district_changes = {}
for k,v in new_ed.iteritems():
    if k not in old_ed:
        new_districts.append(k)
    else:
        for field in ED_FIELDS:
            if new_ed[k][field] != old_ed[k][field]:
                if k not in district_changes:
                    district_changes[k] = {'id':k,
                                            'name_old':'','name_new':'',
                                            'ocdid_old':'','ocdid_new':'',
                                            'identifier_old':'','identifier_new':'',
                                            'type_old':'','type_new':'',
                                            'state_key_old':'','state_key_new':''}
                district_changes[k][field+'_old'] = old_ed[k][field]
                district_changes[k][field+'_new'] = new_ed[k][field]
        del old_ed[k]

print 'Removed districts: {}'.format(len(old_ed))
print 'New districts: {}'.format(len(new_districts))
print 'District changes: {}'.format(len(district_changes))

with open('../json/{}-{}_ed_removed.csv'.format(new_version,old_version),'w') as w:
    for ed in old_ed.keys():
        w.write(ed+'\n')
with open('../json/{}-{}_ed_added.csv'.format(new_version,old_version),'w') as w:
    for ed in new_districts:
        w.write(ed+'\n')
with open('../json/{}-{}_ed_changes.csv'.format(new_version,old_version),'w') as w:
    writer = DictWriter(w,fieldnames=ED_CHANGE_FIELDS)
    writer.writeheader()
    for k,v in district_changes.iteritems():
        writer.writerow(v)




with open(JSON_DIR.format(old_version)+'office.json') as r:
    data = json.load(r)
    for off in data:
        old_off[off['id']] = off
with open(JSON_DIR.format(new_version)+'office.json') as r:
    data = json.load(r)
    for off in data:
        new_off[off['id']] = off

new_office = []
office_changes = {}
for k,v in new_off.iteritems():
    if k not in old_off:
        new_office.append(k)
    else:
        for field in OFF_FIELDS:
            if new_off[k][field] != old_off[k][field]:
                if k not in office_changes:
                    office_changes[k] = {'id':k,
                                            'electoral_district_id_old':'','electoral_district_id_new':'',
                                            'electoral_district_name_old':'','electoral_district_name_new':'',
                                            'name_old':'','name_new':'',
                                            'identifier_old':'','identifier_new':'',
                                            'state_key_old':'','state_key_new':'',
                                            'office_level_old':'','office_level_new':'',
                                            'body_name_old':'','body_name_new':''}
                office_changes[k][field+'_old'] = old_off[k][field]
                office_changes[k][field+'_new'] = new_off[k][field]
        del old_off[k]

print 'Removed offices: {}'.format(len(old_off))
print 'New offices: {}'.format(len(new_office))
print 'Office changes: {}'.format(len(office_changes))

with open('../json/{}-{}_office_removed.csv'.format(new_version,old_version),'w') as w:
    for off in old_off.keys():
        w.write(off+'\n')
with open('../json/{}-{}_office_added.csv'.format(new_version,old_version),'w') as w:
    for off in new_office:
        w.write(off+'\n')
with open('../json/{}-{}_office_changes.csv'.format(new_version,old_version),'w') as w:
    writer = DictWriter(w,fieldnames=OFF_CHANGE_FIELDS)
    writer.writeheader()
    for k,v in office_changes.iteritems():
     #   print v
        writer.writerow(v)




with open(JSON_DIR.format(old_version)+'office_holder.json') as r:
    data = json.load(r)
    for oh in data:
        old_oh[oh['identifier']] = oh
with open(JSON_DIR.format(new_version)+'office_holder.json') as r:
    data = json.load(r)
    for oh in data:
        new_oh[oh['identifier']] = oh

new_office_holder = []
office_holder_changes = {}
for k,v in new_oh.iteritems():
    if k not in old_oh:
        new_office_holder.append(k)
    else:
        for field in OH_FIELDS:
            if new_oh[k][field] != old_oh[k][field]:
                if k not in office_holder_changes:
                    office_holder_changes[k] = {'identifier':k,
                                            'name_old':'','name_new':'',
                                            'id_old':'','id_new':''}
                office_holder_changes[k][field+'_old'] = old_oh[k][field]
                office_holder_changes[k][field+'_new'] = new_oh[k][field]
        del old_oh[k]

print 'Removed office holders: {}'.format(len(old_oh))
print 'New office holders: {}'.format(len(new_office_holder))
print 'Office holder changes: {}'.format(len(office_holder_changes))

with open('../json/{}-{}_office_holder_removed.csv'.format(new_version,old_version),'w') as w:
    for oh in old_oh.keys():
        w.write(old_oh[oh]['id']+'\n')
with open('../json/{}-{}_office_holder_added.csv'.format(new_version,old_version),'w') as w:
    for oh in new_office_holder:
        w.write(oh+'\n')
with open('../json/{}-{}_office_holder_changes.csv'.format(new_version,old_version),'w') as w:
    writer = DictWriter(w,fieldnames=OH_CHANGE_FIELDS)
    writer.writeheader()
    for k,v in office_holder_changes.iteritems():
   #     print v
        writer.writerow(v)

