"""
Print filtered Twitter messages in real-time.

Usage:
    python twitter_stream.py config.json

See:
  - config.json.sample for a sample config.json file
  - https://dev.twitter.com/apps/ generates parameters for "api" parameters
  - https://dev.twitter.com/docs/api/1.1/post/statuses/filter for "search"
"""

import sys
import json
from TwitterAPI import TwitterAPI


def search(params):
    api = TwitterAPI(
        params['api']['consumer_key'],
        params['api']['consumer_secret'],
        params['api']['access_token_key'],
        params['api']['access_token_secret'])

    r = api.request('statuses/filter', params['search'])
    out = open(params['save_tweets'], 'ab')
    for item in r.get_iterator():
        json.dump(item, out, separators=(',', ':'))
        out.write('\n')
        out.flush()

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print __doc__.strip()
        sys.exit(0)

    params = json.load(open(sys.argv[1]))
    search(params)
