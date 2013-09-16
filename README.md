Twitter Stream
==============

An application that constantly monitors one or more keywords.

This runs on UNIX or Cygwin. Tested on Python 2.7. Earlier versions might work.

- pip install TwitterAPI
- Copy `config.json.sample` to `config.json`
- Edit `config.json` to fill the [API keys](https://dev.twitter.com/apps/) and
  [search filters](https://dev.twitter.com/docs/api/1.1/post/statuses/filter)

Run:

    nohup ./run.sh config.json >> tweets.json 2>> error.log &

**Note:** You need to use a different [application](https://dev.twitter.com/apps/)
for each connection
