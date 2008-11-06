
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.datatree.models import *

def PopulateInitialDataTree():
    for i in TreeMap:
        GetNode(i)

# Q = Qualifier/Series/Category
# V = Verb
TreeMap = (
    'Q',
    'Q/Programs',
    'Q/Administrivia',
    'Q/Administrivia/Meetings',
    'Q/Administrivia/OrganizationalProjects',
    'Q/ESP',
    'Q/ESP/Committees',
    'Q/ESP/Committees/Webministry',
    'Q/ESP/Committees/Membership',
    'Q/Community',
    'Q/Community/6_12',
    'Q/Community/6_12/Grade6',
    'Q/Community/6_12/Grade7',
    'Q/Community/6_12/Grade8',
    'Q/Community/6_12/Grade9',
    'Q/Community/6_12/Grade10',
    'Q/Community/6_12/Grade11',
    'Q/Community/6_12/Grade12',
    'Q/Community/Prefrosh',
    'Q/Community/Member',
    'Q/Web',
    'V',
    'V/MIT',
    'V/dbmail',
    'V/dbmail/Subscribe',
    'V/registrar',
    'V/registrar/Deadline',
    'V/registrar/Administer',
    )

