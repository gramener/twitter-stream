'''
Benchmark PostgresQL.

Create a user 'test' with password 'test' with access to a database 'test'.

    $ psql -U postgres
    postgres=# CREATE USER test WITH PASSWORD 'test';
    postgres=# CREATE DATABASE test OWNER test;

'''

import time
import logging
import psycopg2


def benchmark(function):
    def new_function(*args):
        start = time.time()
        function(*args)
        end = time.time()
        logging.info('%6.0fms: %s(%s)', (end - start) * 1000, function.__name__,
                     ', '.join(repr(v) for v in args))
    return new_function


def insert_benchmark(tweets):
    '''How long does it take to insert a large number of JSONB rows?'''

    conn = psycopg2.connect('dbname=test user=test password=test')
    cur = conn.cursor()
    n_tweets = len(tweets)

    def create_table(name, cols):
        cur.execute('DROP TABLE IF EXISTS %s' % name)
        cur.execute('CREATE TABLE %s %s' % (name, cols))
        conn.commit()

    @benchmark
    def commit_every_time(db, n):
        for count in range(n):
            cur.execute('INSERT INTO {:s} (tweet) VALUES (%s)'.format(db),
                        (tweets[count % n_tweets],))
            conn.commit()

    @benchmark
    def commit_at_end(db, n):
        for count in range(n):
            cur.execute('INSERT INTO {:s} (tweet) VALUES (%s)'.format(db),
                        (tweets[count % n_tweets],))
        conn.commit()

    @benchmark
    def commit_multirow(db, n):
        stmt = ','.join(cur.mogrify('(%s)', (tweets[i % n_tweets],)).decode('utf-8')
                        for i in range(n))
        cur.execute('INSERT INTO {:s} (tweet) VALUES {:s}'.format(db, stmt))
        conn.commit()

    test_functions = [commit_every_time, commit_at_end, commit_multirow]

    create_table('benchmark_jsonb', '(id serial PRIMARY KEY, tweet jsonb)')
    [test_fn('benchmark_jsonb', 5000) for test_fn in test_functions]

    create_table('benchmark_json', '(id serial PRIMARY KEY, tweet json)')
    [test_fn('benchmark_json', 5000) for test_fn in test_functions]

    create_table('benchmark_text', '(id serial PRIMARY KEY, tweet text)')
    [test_fn('benchmark_text', 5000) for test_fn in test_functions]

    create_table('benchmark_jsonb_noindex', '(tweet jsonb)')
    [test_fn('benchmark_jsonb_noindex', 5000) for test_fn in test_functions]


if __name__ == '__main__':
    import os

    logging.basicConfig(level=logging.INFO)

    # Change to the directory where this Python file is
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load sample tweets
    tweets = open('tweets.txt').readlines()
    insert_benchmark(tweets)
