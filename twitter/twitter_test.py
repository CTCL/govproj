#!/usr/bin/env python
from csv import DictReader, DictWriter
import requests
from requests_oauthlib import OAuth1
from twitter_config import Secrets, Options

"""
Test script to search twitter for accounts of elected officials. 3 searches
  are performed for each elected official and the search terms vary based on
  the specifics of the office. Config file is used for now to set input and
  output files.

Requirements:
    Python2.7
    requests
    Twitter account info

Constants from twitter_config:
    Secrets.CONSUMER_KEY
    Secrets.CONSUMER_SECRET
    Secrets.ACCESS_TOKEN
    Secrets.ACCESS_TOKEN_SECRET
    Options.URL -- Twitter search url
    Options.OUTPUT_FIELD -- File output fields
    Options.OUTPUT_FILE -- Name of output file
    Options.INPUT_FILE -- Name of input file
    Options.BOARD_TERMS -- terms that indicate using board twitter is okay
"""


def get_results(session, search_term):
    """Connect to the Twitter API and return search results for given term

    Keyword Arguments:
        session -- session object to connect to Twitter
        search_term -- term to search for

    Returns:
        data -- screen_name, description, name, location for 5 closest matches
    """
    params = {'q': search_term, 'page': '1', 'count': '5'}
    response = session.request('GET', Options.URL, params=params)
    data = [{'screen_name': r['screen_name'],
             'description': r['description'],
             'name': r['name'],
             'location': r['location']} for r in list(response.json())]
    return data


def senate_terms(row):
    """Twitter searches for senators:
        'Senator <Name>'
        '<State> <Name>'
        '<Name>'

    Keyword Arguments:
        row -- row of file data to pull from

    Returns:
        list with three search terms
    """
    return ['{} {}'.format('Senator', row['Official Name']),
            '{} {}'.format(row['State'], row['Official Name']),
            '{}'.format(row['Official Name'])]


def house_terms(row):
    """Twitter searches for house members:
        '<State> Representative <Name>'
        '<House District> <Name>'
        '<Name>'

    Keyword Arguments:
        row -- row of file data to pull from

    Returns:
        list with three search terms
    """
    return ['{} Representative {}'.format(row['State'], row['Official Name']),
            '{} {}'.format(row['Electoral District'], row['Official Name']),
            '{}'.format(row['Official Name'])]


def state_leg_terms(row):
    """Twitter searches for state legislators:
        '<State> Legislator <Name>'
        '<Electoral District> <Name>'
        '<Name> <State>'

    Keyword Arguments:
        row -- row of file data to pull from

    Returns:
        list with three search terms
    """
    return ['{} Legislator {}'.format(row['State'], row['Official Name']),
            '{} {}'.format(row['Electoral District'], row['Official Name']),
            '{} {}'.format(row['Official Name'], row['State'])]


def county_board_terms(row):
    """Twitter searches for county board officials:
        '<Name> <Office Name> <County> County'
        '<Name> <County> County'
        '<County> County <State> Goverment'

    Keyword Arguments:
        row -- row of file data to pull from

    Returns:
        list with three search terms
    """
    return ['{} {} {} County'.format(row['Official Name'],
                                     row['Office Name'],
                                     row['Body Represents - County']),
            '{} {} County'.format(row['Official Name'],
                                  row['Body Represents - County']),
            '{} County {} Government'.format(row['Body Represents - County'],
                                             row['State'])]


def county_terms(row):
    """Twitter searches for county officials:
        '<Name> <Office Name> <County> County'
        '<Name> <County> County'
        '<County> County <State> <Office Name>'

    Keyword Arguments:
        row -- row of file data to pull from

    Returns:
        list with three search terms
    """
    return ['{} {} {} County'.format(row['Official Name'],
                                     row['Office Name'],
                                     row['Body Represents - County']),
            '{} {} County'.format(row['Official Name'],
                                  row['Body Represents - County']),
            '{} County {} {}'.format(row['Body Represents - County'],
                                     row['State'],
                                     row['Office Name'])]


def city_terms(row):
    """Twitter searches for city officials:
        '<Name> <Office Name> <City> City'
        '<Name> <City> City'
        '<City> City <Office Name>'

    Keyword Arguments:
        row -- row of file data to pull from

    Returns:
        list with three search terms
    """
    return ['{} {} {} City'.format(row['Official Name'],
                                   row['Office Name'],
                                   row['Body Represents - Muni']),
            '{} {} City'.format(row['Official Name'],
                                row['Body Represents - Muni']),
            '{} City {}'.format(row['Body Represents - Muni'],
                                row['Office Name'])]


def main():
    """Main function establishes connection to the Twitter API using requests,
    reads in the file of elected officials, and runs three searches for each
    official based on the level and type of their office.
    """

    # Establish Twitter connection using OAuth1 from requests
    auth = OAuth1(Secrets.CONSUMER_KEY,
                  Secrets.CONSUMER_SECRET,
                  Secrets.ACCESS_TOKEN,
                  Secrets.ACCESS_TOKEN_SECRET)
    session = requests.Session()
    session.auth = auth

    # ***Count for number of searches, script stops after 50***
    count = 0

    with open(Options.INPUT_FILE, 'r') as r, open(Options.OUTPUT_FILE, 'w') as w:
        reader = DictReader(r)
        writer = DictWriter(w, fieldnames=Options.OUTPUT_FIELDS)
        writer.writeheader()

        for row in reader:
            count += 1
            if row['Office Level'] == 'Federal - Upper':
                search_terms = senate_terms(row)
            elif row['Office Level'] == 'Federal - Lower':
                search_terms = house_terms(row)
            elif row['Office Level'].startswith('State Legislature'):
                search_terms = state_leg_terms(row)
            elif row['Office Level'] == 'County' and any(t in row['Body Name'] for t in Options.BOARD_TERMS):
                search_terms = county_board_terms(row)
            elif row['Office Level'] == 'County':
                search_terms = county_terms(row)
            elif row['Office Level'] == 'City':
                search_terms = city_terms(row)

            output = {'uid': row['UID'],
                      'twitter_name': row['Twitter Name']}

            for i, term in enumerate(search_terms, start=1):
                output['search_term_{}'.format(i)] = term
                output['search_results_{}'.format(i)] = str(get_results(session, term))

            writer.writerow(output)

            # ****Set to break after 50 searches are performed to not hit API
            # limits, could be set to sleep for continued searches***
            if count >= 50:
                break

if __name__ == '__main__':
    main()
