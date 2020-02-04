#!/usr/bin/env python

import re
import os

direction = 'forward'
#direction = 'backward'

#   Note: codefiles.txt obtained by something like
#         'git grep -Il "__author__" -- esp/esp > codefiles.txt'
file = open('codefiles.txt', 'r')

filenames = [r.strip() for r in file.readlines()]

NEW_AUTHOR = "Individual contributors (see AUTHORS file)"
NEW_LICENSE = "AGPL v.3"
NEW_COPYRIGHT = """
This file is part of the ESP Web Site
Copyright (c) %s by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

"""
1 = start (find author)
2 = find date
3 = find rev
4 = find licence
5 = find copyright start
6 = find copyright end
7 = copy rest of file verbatim
"""
for fn in filenames:
    print 'Processing: %s' % fn

    if direction == 'forward':
        curfile = open(fn, 'r')
        outfile = open(fn + '.new', 'w')

        lines = [r.strip('\n') for r in curfile.readlines()]
        state = 1
        copyright_start_line = 0
        copyright_text = ''
        for i in range(len(lines)):
            line = lines[i]
            if state == 1:
                if line.startswith('__author__'):
                    author_dir = line.split('"')
                    print '  Author on line %d: "%s"' % (i + 1, author_dir[-2])
                    if author_dir[-2] == "MIT ESP":
                        print '  -> Rewriting to: "%s"' % NEW_AUTHOR
                        outfile.write('__author__    = "%s"\n' % NEW_AUTHOR)
                    else:
                        outfile.write(line + '\n')
                    state = 2
                    continue
                else:
                    outfile.write(line + '\n')
            elif state == 2:
                outfile.write(line + '\n')
                if line.startswith('__date__'):
                    date_dir = line.split('"')
                    print '  Date on line %d: "%s"' % (i + 1, date_dir[-2])
                    state = 3
                    continue
            elif state == 3:
                outfile.write(line + '\n')
                if line.startswith('__rev__'):
                    rev_dir = line.split('"')
                    print '  Revision on line %d: "%s"' % (i + 1, rev_dir[-2])
                    state = 4
                    continue
            elif state == 4:
                if line.startswith('__license__'):
                    license_dir = line.split('"')
                    print '  License on line %d: "%s"' % (i + 1, license_dir[-2])
                    if license_dir[-2] == "GPL v.2":
                        print '  -> Rewriting to: "%s"' % NEW_LICENSE
                        outfile.write('__license__   = "%s"\n' % NEW_LICENSE)
                    else:
                        outfile.write(line + '\n')
                    state = 5
                    continue
                else:
                    outfile.write(line + '\n')
            elif state == 5:
                if line.startswith('__copyright__'):
                    print '  Copyright start on line %d' % (i + 1)
                    state = 6
                    continue
            elif state == 6:
                if line.startswith('"""'):
                    print '  Copyright end on line %d' % (i + 1)
                    print '  Copyright contents follow'
                    print copyright_text

                    result = re.search('Copyright \(c\) ([-0-9]+)', copyright_text)
                    if result:
                        print '  Copyright date search yielded %s' % result.groups()[0]

                        #   Write new copyright notice
                        outfile.write('__copyright__ = """%s"""\n' % (NEW_COPYRIGHT % result.groups()[0]))
                    else:
                        #   Write old copyright notice if it didn't match
                        outfile.write('__copyright__ = """%s"""\n' % copyright_text)

                    state = 7
                    continue
                copyright_text += '\n' + line
            elif state == 7:
                outfile.write(line + '\n')

        curfile.close()
        outfile.close()

        os.rename(fn, fn + '.old')
        os.rename(fn + '.new', fn)

    elif direction == 'backward':
        os.rename(fn, fn + '.new')
        os.rename(fn + '.old', fn)

file.close()
