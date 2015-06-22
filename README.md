Twitter Streaming App
=====================

This app allows any logged-in user to track Twitter users / keywords / places.
The result will be logged into PostgreSQL.

This app focuses on getting Twitter feeds -- not viewing them. It provides
basic functionality to see the number of tweets, recent tweets, basic filters,
etc. But the intent is to get the data, not process or visualise the data.

On the other hand, it does focus on administration. Re-starting tasks,
monitoring CPU / disk usage, alerting, archiving, etc. are the areas of focus.


## Why?

There is a lot of demand for sourcing Twitter data. Gramener's earlier
[twitter-stream](https://github.com/gramener/twitter-stream) repo fit the bill
for programmers. But the need is for non-programmers to be able to initiate
and monitor their feeds.

Secondly, [twitter-stream](https://github.com/gramener/twitter-stream) stored
the data as flat files. While this is a good format for archival, it is not
great for access.

Thirdly, the earlier approach was quite "heavy". It requires running a process
for every set of keywords. Besides, there's no central monitoring of what
keywords are being tracked -- leading to several abandoned processes and
datasets.

A single lightweight app that allows users to source, monitor and download
Twitter data addresses all of these gaps.

## Setup

- Install [Python 3.4](http://continuum.io/downloads#py34)
- Install required Python modules on Python 3:
  `pip install aiohttp oauthlib`. On Windows, you'll need to get
  [psycopg2](www.lfd.uci.edu/~gohlke/pythonlibs/)
- Install Postgres
- Copy `config.yaml.sample` to `config.yaml` and follow the instructions in
  the file to set up Postgres
- On the command line, run `python3 twitterstream.py`
- Install [Gramex](https://learn.gramener.com/docs/server). This requires
  Python 2
- Run `python gramex.pyc` from this folder and visit the app


## Design choices

- **Python 3**. Python 3 async capabilities are important to leverage.
- **Postgres**. It supports [JSON](http://www.postgresql.org/docs/9.4/static/datatype-json.html)
  natively. We could use MongoDB, but
  [Postgres is OK for immutable data](https://www.compose.io/articles/is-postgresql-your-next-json-database/).
  and Derek Sivers has suggested
  [moving code into Postgres](http://sivers.org/pg), which looks promising.
- **Async**, not threads. We're I/O-limited, not CPU-limited. We'll use
  Twitter's [Streaming API](https://dev.twitter.com/streaming/overview) via
  **[aiohttp](http://aiohttp.readthedocs.org/)** instead of `requests` since
  the latter is blocking, not async. Also, we'll use **psycopg2** not
  SQLAlchemy. We need to minimise footprint. Plus it supports
  [async](http://initd.org/psycopg/docs/advanced.html#asynchronous-support)
- **API**, not an app. `twitterstream.py` is a standalone application that
  monitors Postgres for configuration changes. Gramex provides a web interface
  to the configuration.

Notes:

- We don't need PostgresQL to be too fast. At 1,000 tweets/second, and
  1KB/tweet, we're talking 1MB/second ~ 86GB/day of data, which will lead to a
  storage problem quickly.
- With multirow inserts, we can do well over 1,000 inserts/second on jsonb.
  This is tested in `test/pgbench.py`. Further optimisations are possible. See
  [StackOverflow](http://stackoverflow.com/a/12207237/100904).
- This is a useful article on
  [querying JSON in Postgres](http://schinckel.net/2014/05/25/querying-json-in-postgres/)
- The `requests` library blocks. We need
   for HTTP, and we might also need
  [aiopg](https://github.com/aio-libs/aiopg) for PostgresSQL.


## TODO

- [ ] Postgres partitioning / archival
