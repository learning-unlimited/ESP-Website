
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
    'Q/Web',
    'Q/Web/myesp',
    'Q/Web/about',
    'Q/Web/getinvolved',
    'Q/Web/archives',
    
    'Q/Programs',
    'Q/Programs/Splash',
    
    'V',
    'V/Subscribe',
    'V/Registration',
    'V/Registration/MedicalFiled',
    'V/Registration/LiabilityFiled',
    'V/Registration/Paid',
    'V/Registration/OnSite',
    'V/Deadline',
    'V/Deadline/Registration/Student',
    'V/Deadline/Registration/Student/Applications',
    'V/Deadline/Registration/Student/Catalog',
    'V/Deadline/Registration/Student/Classes',
    'V/Deadline/Registration/Student/Classes/OneClass',
    'V/Deadline/Registration/Student/Confirm',
    'V/Deadline/Registration/Student/ExtraCosts',
    'V/Deadline/Registration/Student/MainPage',
    'V/Deadline/Registration/Student/Payment',
    'V/Deadline/Registration/Teacher',
    'V/Deadline/Registration/Teacher/Catalog',
    'V/Deadline/Registration/Teacher/Classes',
    'V/Deadline/Registration/Teacher/Classes/View',
    'V/Deadline/Registration/Teacher/MainPage',
    'V/Publish',
    'V/Create',
    'V/Flags',
    'V/Flags/UserRole',
    'V/Flags/UserRole/Student',
    'V/Flags/UserRole/Teacher',
    'V/Flags/UserRole/Educator',
    'V/Flags/UserRole/Guardian',
    'V/Flags/UserRole/Administrator',
    'V/Flags/Public',
    'V/Flags/Registration',
    'V/Flags/Registration/Attended',
    'V/Flags/Registration/Teacher',
    'V/Flags/Registration/Confirmed',
    'V/Flags/Registration/Preliminary',
    'V/Flags/Registration/Enrolled',
    'V/Flags/Registration/Applied',
    'V/Flags/Registration/Priority/1',
    'V/Flags/Registration/Priority/2',
    'V/Flags/Registration/Priority/3',
    'V/Flags/Registration/Priority/4',
    'V/Flags/Registration/Priority/5',
    'V/Flags/Registration/Priority/6',
    'V/Flags/Registration/Priority/7',
    'V/Flags/Registration/Priority/8',
    'V/Flags/Registration/Priority/9',
    'V/Administer',
    'V/Administer/Publish',
    'V/Administer/Program',
    'V/Administer/Program',
    'V/Administer/Program/Class',
    'V/Administer/Edit',
    'V/Administer/Edit/QSD',
    'V/Administer/Edit/Class',
    'V/Administer/Edit/Use',
    ]


def genTemplate():
    """ Generates the DataTree tree nodes listed in 'templates' above, including implicit parents (ie. given Q/Foo/Bar, will autogenerate Q/Foo and Q as well, even if they aren't listed)

    Returns a list of DataTree nodes corresponding exactly (in order, target, etc.) to the names in templates """
    
    from esp.datatree.models import DataTree, GetNode, QTree, get_lowest_parent, StringToPerm, PermToString
    node_list = [ DataTree.get_by_uri(i, create=True) for i in tree_template ]
    
    #   Special URI changes to override default tree structure (i.e. URIs start with '/')
    for n in node_list:
        n.expire_uri()

    Q_node = DataTree.objects.get(uri='Q')
    V_node = DataTree.objects.get(uri='V')
    Q_node.uri = 'Q'
    V_node.uri = 'V'

    #   We can't use node_list again, since expire_uri doesn't modify the python object.
    for n in DataTree.objects.filter(uri_correct=False):
        n.get_uri()

        

