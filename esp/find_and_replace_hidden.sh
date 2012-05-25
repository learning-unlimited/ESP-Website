#!/bin/sh

for file in $(grep -lir "_hidden" templates/*)
do
sed -e 's/[a-z]*_hidden/hidden/ig' $file > /tmp/tempfile.tmp
mv /tmp/tempfile.tmp $file
done
