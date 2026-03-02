"""
Automatically import everything from the handlers directory.
"""

import os.path
import glob


files = glob.glob('%s/*.py' %
                  os.path.dirname(__file__)) # get a list of python files

cur_file = os.path.basename(__file__)
if cur_file[-1] == 'c':
    cur_file = os.path.basename(cur_file[:-1])

files = [os.path.basename(file) for file in files ]
# this does some interesting comprehension

files = [ name[:-3] for name in files if name != cur_file]
import re
prog = re.compile(r'^\w+$')
files = [name for name in files if prog.match(name) is not None]
base  = 'esp.program.modules.handlers.'

oldglobals = globals()

files.sort()

for filename in files:

    globals().update(oldglobals)
    mod = __import__(base+filename, globals(), locals(), [filename])

    globals().update(mod.__dict__)


globals().update(oldglobals)
