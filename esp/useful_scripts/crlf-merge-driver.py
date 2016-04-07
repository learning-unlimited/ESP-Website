#!/usr/bin/env python

## Written by David Benjamin

# Usage:
#
# in your git config, add
#
# [merge "merge-line-ending"]
#         name = Merge driver that handles line endings and then calls git merge-file
#         driver = /home/davidben/web/esp-project/crlf-merge-driver.py %A %O %B
#
# and in .gitattributes of the repository add, e.g.,
#
# *.py  merge=merge-line-ending
#


import sys
import subprocess

endings = {'lf': '\n', 'cr': '\r', 'crlf': '\r\n'}

def detect_line_ending(path):
    crlf, lf, cr = 0, 0, 0
    file = open(path, "r")
    for line in file:
        if line.endswith('\r\n'):
            crlf += 1
        elif line.endswith('\r'):
            cr += 1
        elif line.endswith('\n'):
            lf += 1
    file.close()
    biggest = max(crlf, lf, cr)
    if lf == biggest:
        return 'lf'
    if crlf == biggest:
        return 'crlf'
    return 'cr'

def convert_line_ending(path, ending):
    data = ''
    file = open(path, "r")
    for line in file:
        if line.endswith('\r\n'):
            line = line[:-2]
        elif line.endswith('\r'):
            line = line[:-1]
        elif line.endswith('\n'):
            line = line[:-1]
        data += line + endings[ending]
    file.close()
    file = open(path, "w")
    file.write(data)
    file.close()

local_path = sys.argv[1]
base_path = sys.argv[2]
remote_path = sys.argv[3]

final_ending = detect_line_ending(local_path)
convert_line_ending(base_path, final_ending)
convert_line_ending(remote_path, final_ending)

retcode = subprocess.call(["git", "merge-file", local_path, base_path, remote_path])
sys.exit(retcode)
