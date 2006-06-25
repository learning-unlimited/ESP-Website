import unittest
from esp.watchlists.models import Category, Subscription, DatatreeNodeData, Datatree, NoSuchNodeException, NoRootNodeException

class TreeTest(unittest.TestCase):
    def setUp(self):
        # Call PopulateInitialDatatree() in watchlists.models

        

    def tearDown(self):

class OnlyOneRootNode(TreeTest):
    def runTest(self):
        numOfRootNodes = Datatree.objects.filter(parent=NONE,name="ROOT").count()
        assert numOfRootNodes == 1, 'There can only be one ROOT node.  There are ' + str(numOfRootNodes) + '.'
        
