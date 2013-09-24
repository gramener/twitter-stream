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

    r = None
    for user in open(params['followers']['source']):
        user = user.strip()
        if user in followers:
            continue

        r = api.request('followers/ids', {'user_id': user})
        if r.status_code != 200:
            print >>sys.stderr, user, r.content
            break

        ids = followers[user] = r.json()['ids']

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
