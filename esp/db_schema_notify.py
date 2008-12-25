#!/usr/bin/python

"""
Database Schema Change Notifier

    $ ./db_schema_notify.py [commitone] [committwo]

Supply no command line arguments to see changes from the last update.
Supply a single commit to see changes since then.
Supply two commits to see changes between them.
"""

# Make it run on Python 2.5
from __future__ import with_statement

import sys, os

# Use colors?
USE_COLORS = True

# Make xterm and its cousins use pretty colors!
if USE_COLORS:
    def color( n, bright=0 ):
        if n == 0:
            return chr(27) + '[m'
        return '%s[%s;%sm' % ( chr(27), bright, n )
else:
    def color( n, bright=0 ):
        return ''

# Using new subprocess module, since os.popen is going to be deprecated.
# The command needs to be passed as a list, not a string... how annoying.
def pipelines( cmd ):
    """ Pipe in lines of data from a shell command. """
    import subprocess
    return subprocess.Popen( cmd.split(' '), stdout=subprocess.PIPE ).communicate()[0].splitlines()


# Figure out which commits we're comparing.
if len(sys.argv) > 1:
    # Maybe we were passed the revisions to use to use on the command line.
    commits_str = sys.argv[1]
    if '..' not in commits_str:
        if len(sys.argv) > 2:
            commits_str += '..' + sys.argv[2]
        else:
            commits_str += '..HEAD'
else:
    # No command-line arguments. Then use the last change made to HEAD.
    commits_str = 'HEAD@{1}..HEAD'


# Look for changes in esp/db_schema. Save what we don't know how to handle.
unhandled_changes = []
manifest = pipelines( 'git --no-pager diff --summary %s esp/db_schema' % commits_str )
for line in manifest:
    words = line.split()
    if words[0] != 'create':
        # Deleted or modified? Usually shouldn't happen. Warn if it does.
        # Need a better way to deal with branch switching.
        unhandled_changes.append(line)

# If no changes, quit now.
if not manifest:
    print '    No schema changes found.'
    exit(0)


print """%s===============================
%sWARNING: DATABASE SCHEMA CHANGE
%s===============================%s

    Database schema changes have been detected in the following commits.
    We've tried to find and display the authors' update instructions:

""" % ( color(31, 1), color(37, 1), color(31, 1), color(0) )

# Grab the change log for existing files start tweaking it.
changelog_raw = pipelines( 'git --no-pager whatchanged -m %s esp/db_schema' % commits_str )
for line in changelog_raw:
    words = line.split()
    
    # Grr, stupid empty lines
    if not line.strip():
        print color(0)
        continue
    
    # Colorize commits if we can.
    if words[0] == 'commit':
        print color(33, 1) + line + color(33, 0)
        continue
    
    # Check out the file listing
    if line[0] == ':':
        # Dump text files attached to each commit.
        if words[-1][-4:] == '.txt':
            fname = words[-1]
            print '%s%s:%s' % ( color(32, 0), fname, color(0) )
            os.system( 'cat %s' % fname )
    else:
        # Dump ordinary lines.
        print line

if unhandled_changes:
    print """
%s-----
Other changes detected%s

    The following changes may or may not affect the database schema.
    If you just switched branches, they probably do...
%s""" % ( color(37, 1), color(0), color(36, 0) )
    for c in unhandled_changes:
        print c
    print color(0)

print """
%s-----
%sTo see this message again before the next checkout or merge, run:
    $ %s%s/db_schema_notify.py%s
You can also pass specific commits as arguments to this script, to see the
    changes between two commits or between a commit and the current HEAD.
""" % ( color(37, 1), color(0), color(32, 1), os.getcwd(), color(0) )

