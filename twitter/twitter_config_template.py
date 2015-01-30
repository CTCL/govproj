class Secrets(object):
    # fill this in
    CONSUMER_KEY = ''
    CONSUMER_SECRET = ''
    ACCESS_TOKEN = ''
    ACCESS_TOKEN_SECRET = ''


class Options(object):
    # Basically just grouped everything else here
    URL = 'https://api.twitter.com/1.1/users/search.json'
    OUTPUT_FIELDS = ['uid', 'twitter_name',
                     'search_term_1', 'search_results_1',
                     'search_term_2', 'search_results_2',
                     'search_term_3', 'search_results_3']
    OUTPUT_FILE = 'twitter_search_results.csv'
    INPUT_FILE = 'example_office_holders.csv'
    BOARD_TERMS = ['Board', 'County Legislature', 'City Council']
