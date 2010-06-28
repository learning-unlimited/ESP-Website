#!/usr/bin/python

import sys
import re

def grep(string,list):
    expr = re.compile(string, re.I)
    return (elem for elem in (i.strip() for i in list) if expr.match(elem))

assert len(sys.argv) == 2, "Must specify a word!"

word = sys.argv[1]
variants = []

for i in xrange(len(word)):
    variants.append(word[:i] + "." + word[i+1:])

regex = r'^(%s)$' % "|".join(variants)

for i in grep(regex, sys.stdin):
    if i.upper() != word.upper():
        print i
