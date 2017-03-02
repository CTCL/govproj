from __future__ import print_function
from datetime import datetime, timedelta
from jira import JIRA
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from config import jira

jira = JIRA(options={'server':'https://techandciviclife.atlassian.net/'},
            basic_auth=(jira['username'], jira['password']))

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


six_hours_ago = datetime.now() - timedelta(days=30)
credentials = get_credentials()
http = credentials.authorize(httplib2.Http())
discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                'version=v4')
service = discovery.build('sheets', 'v4', http=http,
                          discoveryServiceUrl=discoveryUrl)

spreadsheetId = '1qFHDHoIMkDsd197PEggGdnu5ix1cd0nVG_dlAJycc60'
result = service.spreadsheets().values().get(
    spreadsheetId=spreadsheetId, range='Form Responses 1!A2:E').execute()
reports = [report for report in result.get('values', [])
           if datetime.strptime(report[0],
                                '%m/%d/%Y %H:%M:%S') >= six_hours_ago]

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
    print(report)
    jira.create_issue(project='GP',
                      summary=summary,
                      issuetype={'name': 'Task'},
                      description=body,
                      assignee={'name':'sarah'},
                      customfield_10200={'value': 'Other/ N/A'},
                      labels=['google-report'])
    break
