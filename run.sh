#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

while true
do
    python $DIR/twitter_stream.py $*
    sleep 1
done
