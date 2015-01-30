from csv import DictReader,DictWriter
from os import listdir
import smtplib

STAGING_DIR = '../staging/'
# Stores the following fields: email, ids, names
EMAILED_FILE = 'emails_sent.csv'
OFFICIAL_FIELDS = ['Office Name','Official Name','Official Party','Phone','Mailing Address','Website','Email','Facebook URL','Twitter Name','Google Plus URL','Wiki Word','Youtube']

email_fields = {}
temp_emailed_data = {}
with open(EMAILED_FILE,'r') as r:
    reader = DictReader(r)
    email_fields = reader.fieldnames
    for row in reader:
        temp_emailed_data[row['email']] = row

files = listdir(STAGING_DIR)
row_data = {}
for f in files:
    if f.startswith('.'):
        continue
    if not f.startswith('AL'):
        continue
    print f
    with open(STAGING_DIR + f, 'rU') as r:
        reader = DictReader(r)
        for row in reader:
            email = row['Email']
            if not email or email in temp_emailed_data:
                continue
            if email not in row_data:
                row_data[email] = []
            row_data[email].append(row)

print 'You are about to email {} office holders, are you sure you want to continue?'.format(len(row_data))
yes_no = raw_input('Y/N: ')

if yes_no != 'Y':
    exit()

# Option for environment variables?
email_sender = raw_input('Email Address: ')
pw = raw_input('Password: ')

session = smtplib.SMTP('smtp.gmail.com', 587)
session.ehlo()
session.starttls()
session.login(email_sender,pw)

count = 0
for k,v in row_data.iteritems():
    if len(v) > 1:
        continue
    else:
        k = 'michael@neworganizing.com'
        count += 1
        if count > 5:
            break
        header = '\r\n'.join(['from: {}'.format(email_sender),
                                'subject: Better Test Email {}'.format(count),
                                'to: {}'.format(k),
                                'mime-version: 1.0',
                                'content-type: text/plain'])
        body = '{} {},\r\n\r\n'.format(v[0]['Office Name'],v[0]['Official Name'])
        body += 'We are working on a project to collect official information from elected officials to help connect people to their representatives. We appreciate you helping us improve this data. The following is the information we have collected for your position:\r\n\r\n'
        empty_fields = []
        for f in OFFICIAL_FIELDS:
            if v[0][f]:
                body += '{}: {}\r\n\r\n'.format(f,v[0][f])
            else:
                empty_fields.append(f)
        body += '\r\n\r\nPlease confirm or send us updated information for the fields above'
        if len(empty_fields) > 1:
            body += '\r\n\r\nWe also would appreciate information on the following fields: ' + ', '.join(empty_fields)
        body += '\r\n\r\nThank you for Democracy!\r\nMike'
        # create body
        content = header + '\r\n\r\n' + body
        session.sendmail(email_sender, k, content)
        print k
        print content
        # Try/Catch for email errors?
        temp_emailed_data[v[0]['Email']] = {'email':v[0]['Email'],'ids':v[0]['UID'],'names':v[0]['Official Name']}

with open(EMAILED_FILE,'w') as w:
    writer = DictWriter(w,fieldnames=email_fields)
    writer.writeheader()
    for k,v in temp_emailed_data.iteritems():
        writer.writerow(v)
