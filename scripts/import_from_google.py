from __future__ import print_function
from argparse import ArgumentParser
from datetime import datetime, timedelta
from jira import JIRA
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage
from os import path

import httplib2
import imp
import sys

arg_parser = ArgumentParser(prog='import_from_google.py')
arg_parser.add_argument('--config', required=True)
args = arg_parser.parse_args()

try:
    config = imp.load_source('config', args.config)
except IOError:
    sys.exit('Error: Config file not found.')

jira = JIRA(options={'server': config.jira['server']},
            basic_auth=(config.jira['username'], config.jira['password']))

def google_credentials():
    home_dir = path.expanduser('~')
    credential_dir = path.join(home_dir, '.credentials')
    if not path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = path.join(credential_dir,
                                'sheets.googleapis.com.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(
            config.google['client_secret_file'],
            config.google['scope'])
        flow.user_agent = config.google['user_agent']
        credentials = tools.run_flow(flow, store,
                                     tools.argparser.parse_args([
                                         '--noauth_local_webserver']))

    return credentials

def parse_date(string):
    return datetime.strptime(string, '%m/%d/%Y %H:%M:%S')

one_hour_ago = datetime.now() - timedelta(hours=1)
credentials = google_credentials()
http = credentials.authorize(httplib2.Http())
discovery_url = ('https://sheets.googleapis.com/$discovery/rest?'
                'version=v4')
service = discovery.build('sheets', 'v4', http=http,
                          discoveryServiceUrl=discovery_url)

spreadsheetId = config.google['spreadsheet_id']
result = service.spreadsheets().values().get(
    spreadsheetId=spreadsheetId, range='Form Responses 1!A2:E').execute()
reports = [report for report in result.get('values', [])
           if parse_date(report[0]) + timedelta(hours=3) >= one_hour_ago]

for report in reports:
    try:
        summary = report[2]
    except IndexError:
        continue # no useful information in report

    description = report[3]
    is_now = report[4]

    try:
        should_be = report[5]
    except IndexError:
        should_be = '[blank]'

    try:
        other_info = report[6]
    except IndexError:
        other_info = '[blank]'

    body = '''Which best describes the issue you're reporting?
{}

What is currently being returned by the API?
{}

What is the correct information the API should be returning?
{}

Any other information you think may be important to share with us?
{}
'''.format(description, is_now, should_be, other_info)

    jira.create_issue(project='GP',
                      summary=summary,
                      issuetype={'name': 'Google Issue'},
                      description=body,
                      assignee={'name':'sarah'},
                      customfield_10200={'value': 'Other/ N/A'},
                      labels=['google-report'])
