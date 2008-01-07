
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

tree_template = [
    'Q',
    'Q/Programs/Splash/2006_Fall',
    'Q/Programs/Splash/Templates',
    'Q/Programs/Splash/2006_Fall/Templates/Classrooms',
    'Q/Programs/Splash/2006_Fall/Templates/TimeSlots',
    'Q/Programs/Splash/2006_Fall/Templates/Resources',
    'Q/Programs/Splash/2006_Fall/Templates/Classes',
    'Q/PasswordRecovery',
    'Q/ESP/Committees',
    'Q/ESP/Committees/Webministry/Critical',
    'Q/Web',
    'Q/Web/Splash',
    'Q/Community',
    'Q/Community/6_12',
    'Q/Community/6_12/Grade6',
    'Q/Community/6_12/Grade7',
    'Q/Community/6_12/Grade8',
    'Q/Community/6_12/Grade9',
    'Q/Community/6_12/Grade10',
    'Q/Community/6_12/Grade11',
    'Q/Community/6_12/Grade12',

    'V',
    'V/Finished',
    'V/Subscribe',
    'V/Registration',
    'V/Registration/Livermore',
    'V/Registration/MedicalFiled',
    'V/Registration/LiabilityFiled',
    'V/Registration/Paid',
    'V/Registration/OnSite',
    'V/Registration/Student',
    'V/Deadline',
    'V/Deadline/Registration/Student',
    'V/Deadline/Registration/Teacher',
    'V/Deadline/Registration/Teacher/Class',
    'V/Deadline/Registration/Student/Catalog',
    'V/Deadline/Registration/Student/Classes',
    'V/Publish',
    'V/Create',
    'V/Flags',
    'V/Flags/Deadline',
    'V/Flags/Deadlines/Teacher',
    'V/Flags/UserRole',
    'V/Flags/UserRole/Student',
    'V/Flags/UserRole/Teacher',
    'V/Flags/UserRole/Educator',
    'V/Flags/UserRole/Guardian',
    'V/Flags/Public',
    'V/Flags/Registration',
    'V/Flags/Registration/Attended',
    'V/Flags/Registration/Teacher',
    'V/Flags/Registration/Confirmed',
    'V/Flags/Registration/Preliminary',
    'V/Flags/Class',
    'V/Flags/Class/RoomAssigned',
    'V/Flags/Class/Scheduled',
    'V/Flags/Class/Finished',
    'V/Flags/Class/Proposed',
    'V/Flags/Class/Approved',
    'V/Digest',
    'V/Administer',
    'V/Administer/Publish',
    'V/Administer/Program',
    'V/Administer/Program',
    'V/Administer/Program/Class',
    'V/Administer/Edit',
    'V/Administer/Edit/QSC',
    'V/Administer/Edit/QSD',
    'V/Administer/Edit/Use',
    'V/Subscribe',
    ]


def genTemplate():
    """ Generates the DataTree tree nodes listed in 'templates' above, including implicit parents (ie. given Q/Foo/Bar, will autogenerate Q/Foo and Q as well, even if they aren't listed)

    Returns a list of DataTree nodes corresponding exactly (in order, target, etc.) to the names in templates """
    
    from esp.datatree.models import DataTree
    node_list = [ DataTree.get_by_uri(i, create=True) for i in tree_template ]
    
    #   Special URI changes to override default tree structure (i.e. URIs start with '/')
    for n in node_list:
        n.expire_uri()

    Q_node = DataTree.objects.get(uri__endswith='Q')
    V_node = DataTree.objects.get(uri__endswith='V')
    Q_node.uri = 'Q'
    V_node.uri = 'V'
    for n in node_list:
        n.get_uri()

        

