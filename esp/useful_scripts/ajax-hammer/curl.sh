#!/bin/bash

HOSTNAME="esp.mit.edu:81"

curl -c cookies.txt -b cookies.txt -L -d @login.txt "http://$HOSTNAME/myesp/login/" >/dev/null 2>&1

while (true); do
    echo "Registering for class (pid $$)"
    curl -c cookies.txt -b cookies.txt -L -d @post_class.txt "http://$HOSTNAME/learn/Spark/2010/ajax_addclass" >/dev/null 2>&1
    echo "De-registering from class (pid $$)"
    curl -c cookies.txt -b cookies.txt -L "http://$HOSTNAME/learn/Spark/2010/ajax_clearslot/429?sec_id=3323" >/dev/null 2>&1
done

