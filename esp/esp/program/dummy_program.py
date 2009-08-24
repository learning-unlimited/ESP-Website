""" Code to create the dummy program needed for profile storage. """

from esp.datatree.models import *
from esp.program.models import Program

def init_dummy_program():
    """ Create the profile storage dummy program. Intended to be idempotent. """
    root_node = DataTree.get_by_uri('Q/Programs/Dummy_Programs/Profile_Storage', create=True)
    root_node.friendly_name = 'Program for Profile Information'
    root_node.save()
    
    Program.objects.get_or_create( anchor=root_node, defaults={
        'grade_min': 13, 'grade_max': 13,
        'class_size_min': 9999, 'class_size_max': 9999 } )

