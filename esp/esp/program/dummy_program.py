""" Code to create the dummy program needed for profile storage. """

from esp.datatree.models import *
from esp.program.models import Program

def init_dummy_program():
    root_node = DataTree.get_by_uri('Q/Programs/Dummy_Programs/Profile_Storage', create=True)
    root_node.friendly_name = 'Program for Profile Information'
    root_node.save()
    
    np = Program(anchor=root_node)
    np.grade_min = 13
    np.grade_max = 13
    np.class_size_min = 9999
    np.class_size_max = 9999
    np.save()
    
    