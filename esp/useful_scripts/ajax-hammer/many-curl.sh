#!/bin/sh

PIDS=""
if [ -z "$1" ]; then
    NUM_ITERS="8"
else
    NUM_ITERS="$1"
fi

for i in `jot $NUM_ITERS`; do
    ./curl.sh &
    PIDS="$PIDS $!"
done

trap "echo '$PIDS' | xargs kill ; exit 0" INT

# Sleep forever, waiting for a sigint
while (true); do
    sleep 10000000
done
