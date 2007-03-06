from esp.unittest.unittest import TestCase, TestSuite
from esp.datatree.models import DataTree, GetNode, StringToPerm, PermToString
from esp.setup.TreeMap import PopulateInitialDataTree, TreeMap

class TreeTest(TestCase):
    usergrouptree_nodes = []
    sitetree_nodes = []
    
    def setUp(self):
        """ Create a generic basic testing DataTree, with relevant node data """
        for st in TreeMap:
            if 'Q' in st:
                self.sitetree_nodes.append( st )
            if 'V' in st:
                self.usergrouptree_nodes.append( st )
        
        PopulateInitialDataTree()

        for i in self.usergrouptree_nodes:
            GetNode(i)

        for i in self.sitetree_nodes:
            GetNode(i)

    def tearDown(self):
        # How do I get rid of a recursively-created tree,
        # if I don't know which elements in it were there
        # to begin with?
        pass

class OnlyOneRootNode(TreeTest):
    """ Verify that there is only one ROOT node """
    def runTest(self):
        numOfRootNodes = DataTree.objects.filter(parent=None,name="ROOT").count()
        assert numOfRootNodes == 1, 'There can only be one ROOT node.  There are ' + str(numOfRootNodes) + '.'
        
class AllNodesExist(TreeTest):
    def runTest(self):
        """ Do all the sample nodes in TreeTest exist? """
        # Hack to get the root node easily; this isn't currently defined behavhior
        # (maybe it should be?)
        root = GetNode('')

        for node in self.usergrouptree_nodes:
            # Raises a NoSuchNodeException if the node doesn't exist
            root.tree_decode(StringToPerm(node))

        for node in self.sitetree_nodes:
            # Raises a NoSuchNodeException if the node doesn't exist
            root.tree_decode(StringToPerm(node))

class Test_DataTreeFunctions(TreeTest):
    root = GetNode('')

    def testChildren(self):
        """  Test the 'children()' procedure in DataTree """
        assert self.root.children == DataTree.objects.filter(parent_pk=self.root.id), 'ROOT node\'s children don\t match root.children()'

        # Pick an arbitrary subnode to test
        # I suppose we should care *which* subnode gets tested.  Oh well.
        arbitrary_subnode = self.root.children()[-1]

        assert arbitrary_subnode.children == DataTree.objects.filter(parent_pk=arbitrary_subnode.id)

    def testRefactor(self):
        """ See if all nodes in the tree are still in the tree after a refactor() """
        for node in DataTree.objects.all():
            assert node.is_antecedent(self.root) & self.root.is_descendant(node), 'Node ' + str(node) + ' is not registered in the tree'

        self.root.refactor()
        
        for node in DataTree.objects.all():
            assert node.is_antecedent(self.root) & self.root.is_descendant(node), 'Node ' + str(node) + ' is not registered in the tree, post- refactor()'


datatreeTestSuite = TestSuite()
datatreeTestSuite.addTest(OnlyOneRootNode)
datatreeTestSuite.addTest(AllNodesExist)
datatreeTestSuite.addTest(Test_DataTreeFunctions)
