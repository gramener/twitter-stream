'''Track Twitter via Streaming API'''

# How this application works
# --------------------------
# There are 4 tasks that this app runs in parallel:
#   - run_streams:          Monitor the config table and runs a stream_tweets task for each config
#       - stream_tweets:    Use the Twitter Streaming API and writes tweets into queue
#   - save_tweets:          Save what's on the queue into a data store
#   - show_counts:          Display count of tweets on the console

import os
import sys
import logging
import asyncio              # Requires Python 3.4
import aiohttp              # 3rd-party asyncio HTTP library
import psycopg2             # Postgres library
import traceback
import oauthlib.oauth1
from urllib.parse import urlencode
from collections import namedtuple, Counter
from logging.handlers import RotatingFileHandler


logger = logging.getLogger('twitterstream')
queue = asyncio.Queue()
Event = namedtuple('Event', ['run_id', 'data'])
total_count = Counter()


@asyncio.coroutine
def run_streams(db, sleep, table='config'):
    '''Monitor the config table and runs a stream_tweets task for each config'''
    db.cur.execute('CREATE TABLE IF NOT EXISTS %s (run_id text PRIMARY KEY, config jsonb)' % table)
    db.conn.commit()

    Run = namedtuple('Run', ['task', 'data'])
    params = {'follow', 'track', 'locations'}
    runs = {}
    last_modified = 0
    while True:
        db.cur.execute('SELECT * FROM %s' % table)
        config = dict(db.cur.fetchall())
        for run_id, conf in config.items():
            data = urlencode([
                (key, ','.join(sorted(conf[key])))
                for key in conf
                if key in params])
            oauth = oauthlib.oauth1.Client(
                conf['consumer_key'], conf['consumer_secret'],
                conf['access_token'], conf['access_secret'])
            if run_id in runs:
                if runs[run_id].task.done():
                    try:
                        runs[run_id].task.result()
                    except Exception as error:
                        msg = ''.join(traceback.format_exception(*sys.exc_info()))
                        logger.error('Exception:%s', msg)
                else:
                    if runs[run_id].data == data:
                        continue
                    runs[run_id].task.cancel()
            logger.info('Running:%s:%s',
                        run_id, {key: val for key, val in conf.items() if key in params and val})
            runs[run_id] = Run(data=data, task=loop.create_task(
                stream_tweets(oauth=oauth, run_id=run_id, data=data)))
        # Cancel runs that no loger exist in config
        for run_id, run in runs.items():
            if run_id not in config:
                run.task.cancel()
        yield from asyncio.sleep(sleep)


@asyncio.coroutine
def stream_tweets(oauth, run_id, data):
    '''Use the Twitter Streaming API and writes tweets into queue'''
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
            logger.warning('HTTP %d: %ss retry: %s', response.status, backoff, result)
            response.close()
            yield from asyncio.sleep(backoff)
        # For non-recoverable errors, just give up
        elif response.status != 200:
            result = yield from response.read()
            logger.error('HTTP %d: %s', response.status, result)
            response.close()
            return
        else:
            connection = True

    logger.info('Connected:%s', run_id)
    try:
        reader = response.content
        while not reader.at_eof():
            line = yield from reader.readline()
            if line.strip():
                yield from queue.put(Event(run_id=run_id, data=line.decode('utf-8')))
            else:
                logger.debug('Blank line:%s', run_id)
    finally:
        logger.info('Disconnect:%s', run_id)
        response.close()


@asyncio.coroutine
def save_tweets(db, sleep, table='tweets'):
    '''Save what's on the queue into a data store'''
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
        total_count.update(counter)
        logger.debug('Saving:%s', str(counter))
        db.cur.execute('INSERT INTO %s (run, tweet) VALUES ' % table + ','.join(tweets))
        db.conn.commit()


@asyncio.coroutine
def show_counts(sleep):
    '''Display count of tweets on the console'''
    while True:
        logger.info('Tweets:%s', total_count)
        total_count.subtract(total_count)
        yield from asyncio.sleep(sleep)


if __name__ == '__main__':
    import yaml
    import subprocess

    folder = os.path.dirname(os.path.realpath(__file__))
    setup = yaml.load(open(os.path.join(folder, 'config.yaml')))

    # We'll log WARNINGS into max 2MB log files called twitterstream.log.
    # Up to 10 archives will be created: twitterstream.log.1, twitterstream.log.2
    if 'logfile' in setup:
        handler = RotatingFileHandler(filename=setup['logfile'], maxBytes=2000000, backupCount=10)
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter('{asctime},{levelname:8s},"{message}"',
                                      datefmt='%Y-%M-%d %H:%M:%S', style='{')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # We'll log everything to console. Just redirect to /dev/null if you don't want
    handler = logging.StreamHandler()
    formatter = logging.Formatter('{asctime}:{name}:{levelname}:{message}',
                                  datefmt='%Y-%m-%d %H:%M:%S', style='{')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Set logging level to loglevel in config.yaml. Default to logging.INFO
    logger.setLevel(getattr(logging, setup.get('loglevel', 'info').upper(), logging.INFO))

    # We use a common data store (Postgres) to read config and save tweets
    conn = psycopg2.connect(
        database=setup.get('database'),
        user=setup.get('user'),
        password=setup.get('password'),
        host=setup.get('host'))
    DB = namedtuple('DB', ['conn', 'cur'])
    db = DB(conn=conn, cur=conn.cursor())

    # Run all the main tasks
    count_every, reload_every = setup.get('count_every', 60), setup.get('reload_every', 10)
    loop = asyncio.get_event_loop()
    loop.create_task(save_tweets(db, sleep=setup.get('save_every', 1)))
    loop.create_task(run_streams(db, sleep=reload_every))
    loop.create_task(show_counts(sleep=count_every))

    try:
        version = subprocess.check_output(['git', 'log', '-1', '--pretty=%h'])
        version = version.decode('utf-8').strip()
    except OSError:
        version = 'unknown (no git)'
    logger.info('Started version %s. %ds: logging. %ds: reload config',
                version, count_every, reload_every)

    loop.run_forever()
    loop.close()
