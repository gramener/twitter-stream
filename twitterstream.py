'''Track Twitter via Streaming API'''

import os
import asyncio
import aiohttp
import logging
import psycopg2
import oauthlib.oauth1
from collections import namedtuple, Counter
from urllib.parse import urlencode


queue = asyncio.Queue()
Event = namedtuple('Event', ['run_id', 'data'])


def serialize(args, keys=('follow', 'track', 'locations')):
    return urlencode([
        (key, ','.join(sorted(args[key])))
        for key in keys
        if args.get(key)
    ])


@asyncio.coroutine
def stream_tweets(oauth, run_id, data):
    '''Push tweets into queue. That's it.'''
    url = 'https://stream.twitter.com/1.1/statuses/filter.json'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    url, headers, data = oauth.sign(url, 'POST', body=data, headers=headers)

    # Reconnection strategy: https://dev.twitter.com/streaming/overview/connecting
    connection, backoff = False, 0
    while not connection:
        response = yield from aiohttp.request('POST', url, data=data, headers=headers)
        # For recoverable HTTP errors, back off exponentially (from 60s for 420, 5s for rest)
        if response.status in {420, 429} or response.status >= 500:
            backoff = backoff * 2 if backoff else 60 if response.status == 420 else 5
            result = yield from response.read()
            logging.warning('HTTP %d: %ss retry: %s', response.status, backoff, result)
            response.close()
            yield from asyncio.sleep(backoff)
        # For non-recoverable errors, just give up
        elif response.status != 200:
            result = yield from response.read()
            logging.error('HTTP %d: %s', response.status, result)
            response.close()
            return
        else:
            connection = True

    logging.info('Connected:%s', run_id)
    try:
        reader = response.content
        while not reader.at_eof():
            line = yield from reader.readline()
            if line.strip():
                yield from queue.put(Event(run_id=run_id, data=line.decode('utf-8')))
            else:
                logging.debug('Blank line:%s', run_id)
    finally:
        logging.info('Disconnect:%s', run_id)
        response.close()


@asyncio.coroutine
def save_tweets(db, sleep, table='tweets'):
    '''Save tweets from queue into database'''
    db.cur.execute('CREATE TABLE IF NOT EXISTS %s (run text, tweet jsonb)' % table)
    db.conn.commit()
    while True:
        while queue.qsize() == 0:
            yield from asyncio.sleep(sleep)
        counter, tweets = Counter(), []
        for i in range(queue.qsize()):
            event = queue.get_nowait()
            counter[event.run_id] += 1
            tweets.append(db.cur.mogrify('(%s, %s)', (event.run_id, event.data)).decode('utf-8'))
        logging.info('Saving:%s', str(counter))
        db.cur.execute('INSERT INTO %s (run, tweet) VALUES ' % table + ','.join(tweets))
        db.conn.commit()


@asyncio.coroutine
def run_streams(db, sleep, table='config'):
    db.cur.execute('CREATE TABLE IF NOT EXISTS %s (run_id text PRIMARY KEY, config jsonb)' % table)
    db.conn.commit()
    Run = namedtuple('Run', ['task', 'data'])
    runs = {}
    last_modified = 0
    while True:
        db.cur.execute('SELECT * FROM %s' % table)
        config = dict(db.cur.fetchall())
        for run_id, conf in config.items():
            data = serialize(conf)
            oauth = oauthlib.oauth1.Client(
                conf['consumer_key'], conf['consumer_secret'],
                conf['access_token'], conf['access_secret'])
            if run_id in runs:
                if runs[run_id].data == data:
                    continue
                runs[run_id].task.cancel()
            logging.info('Running:%s', run_id)
            runs[run_id] = Run(data=data, task=loop.create_task(
                stream_tweets(oauth=oauth, run_id=run_id, data=data)))
        # Cancel runs that no loger exist in config
        for run_id, run in runs.items():
            if run_id not in config:
                run.task.cancel()
        yield from asyncio.sleep(sleep)


if __name__ == '__main__':
    import yaml

    folder = os.path.dirname(os.path.realpath(__file__))
    setup = yaml.load(open(os.path.join(folder, 'config.yaml')))

    conn = psycopg2.connect(
        database=setup.get('database'),
        user=setup.get('user'),
        password=setup.get('password'),
        host=setup.get('host'))
    DB = namedtuple('DB', ['conn', 'cur'])
    db = DB(conn=conn, cur=conn.cursor())

    logging.basicConfig(level=getattr(logging, setup.get('loglevel', 'info').upper(), logging.INFO))

    loop = asyncio.get_event_loop()
    loop.create_task(save_tweets(db, sleep=setup.get('save_every', 1)))
    loop.create_task(run_streams(db, sleep=setup.get('reload_every', 10)))
    logging.info('Started server')
    loop.run_forever()
    loop.close()
