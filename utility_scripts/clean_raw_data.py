import chardet
from os import listdir
from csv import DictReader,DictWriter
import json

TEST_DIR = '../../social_media_collection/office_holders/'
EMPTY_CHARS = ['\xb4','\xbe','\xe4','\xbd','\x95','\xb7','\xca','\xd0','\xe6','\xa5','\x91','\xab']
SPACE_CHARS = ['\xa0\xb7\xa0','\xa0']
QUOTE_CHARS = ['\x92','\xea','\xd5','\x93','\x94','\x90','\xcd','\xd2','\xd3']

def encoding_issues(f):
    issues = 0
    data = []
    with open(TEST_DIR + f,'r') as r:
        reader = DictReader(r)
        fields = reader.fieldnames
        for row in reader:
            uid = row['UID']
            try:
                json.dumps(row)
            except:
                issues += 1
                for k,v in row.iteritems():
                    # Should eventually change this to make them valid utf-8 characters
                    row[k] = v.replace('\x96','n').replace('\xf1','n').replace('\xfa','u').replace('\xe1','a').replace('\xe9','e').replace('\xed','i').replace('\xf6','o').replace('\x87','a').replace('\xf3','o').replace('\xf8','o').replace('\xe8','e')
                    row[k] = v.translate(None,''.join(EMPTY_CHARS))
                    if f.startswith('TN'):
                        print row
                    row[k] = v.translate(' ',''.join(SPACE_CHARS))
                    row[k] = v.translate('\'',''.join(QUOTE_CHARS))
                    # char_check = chardet.detect(v)
                    # encoding = char_check['encoding']
                json.dumps(row)
            data.append(row)
    if issues > 0:
        print 'Encoding Issues: {}'.format(issues)
        with open(TEST_DIR + '_' + f,'w') as w:
            writer = DictWriter(w,fieldnames=fields)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        print 'Test file diffs:'
        print 'diff \'{0}{1}\' \'{0}_{1}\''.format(TEST_DIR,f) 
        return True
    return False

def space_issues(f):
    issues = 0
    data = []
    with open(TEST_DIR+f,'r') as r:
        reader = DictReader(r)
        fields = reader.fieldnames
        for row in reader:
            for k,v in row.iteritems():
                row[k] = ' '.join(v.split())
            data.append(row)
   # if not f.startswith('_'):
   #     f = '_' + f
    with open(TEST_DIR+f,'w') as w:
        writer = DictWriter(w,fieldnames=fields)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

files = listdir(TEST_DIR)
for f in files:
    if f.startswith('.') or f.startswith('_') or not f.endswith('.csv'):
        continue
    else:
        print 'Checking {}...'.format(f)
        if encoding_issues(f):
            f = '_'+f
        space_issues(f)

