"""
Print filtered Twitter messages in real-time.

Usage:
    python twitter_stream.py config.json

config.json must have the following structure:

    {
        "api": {
            "consumer_key"        : "...",
            "consumer_secret"     : "...",
            "access_token_key"    : "...",
            "access_token_secret" : "..."
        },
        "search": {
            "track": "keywords"
        }
    }

See:
  - https://dev.twitter.com/apps/ generates parameters for "api"
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

    api.request('statuses/filter', params['search'])
    out = open(params.get('save'), 'w') if 'save' in params else sys.stdout
    for item in api.get_iterator():
        json.dump(item, out, separators=(',', ':'))
        out.write('\n')
        out.flush()

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print __doc__.strip()
        sys.exit(0)

    params = json.load(open(sys.argv[1]))
    search(params)
