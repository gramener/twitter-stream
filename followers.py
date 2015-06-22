"""
Finds followers for a list of users.

Usage:
    python followers.py config.json

See:
  - config.json.sample for a sample config.json file
"""

import os
import sys
import json
import time
import gzip
import pandas as pd
from TwitterAPI import TwitterAPI

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print __doc__.strip()
        sys.exit(0)

    params = json.load(open(sys.argv[1]))

    params.get('users')
    api = TwitterAPI(
        params['api']['consumer_key'],
        params['api']['consumer_secret'],
        params['api']['access_token_key'],
        params['api']['access_token_secret'])

    followers = {}
    target = params['followers']['target']
    if os.path.exists(target):
        followers = json.load(open(target))

    src = params['followers']['source']
    src = gzip.open(src) if src.endswith('.gz') else open(src)
    tweets = pd.Series([l for l in src if l.strip()]).apply(json.loads)

    r = None
    for tweet in tweets:
        if 'user' not in tweet:
            continue

        user = tweet['user']['id_str']
        if user in followers:
            continue

        r = api.request('followers/ids', {'user_id': user}).response
        if r.status_code != 200:
            print >>sys.stderr, user, r.content

        js = r.json()
        if 'ids' in js:
            ids = followers[user] = js['ids']
        else:
            ids = []

        limit = r.headers['x-rate-limit-remaining']
        print >>sys.stderr, '%s: %d followers. %s limit' % (
            user, len(ids), limit)
        if limit == '0':
            break

    json.dump(followers, open(target, 'w'))

    # Tell the script the # seconds it should wait before next run
    sleep = 15 * 60
    if r is not None and 'x-rate-limit-reset' in r.headers:
        sleep = int(r.headers['x-rate-limit-reset']) - time.time()
    print int(sleep)
