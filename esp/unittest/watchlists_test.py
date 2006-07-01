from esp.unittest.unittest import TestCase, TestSuite
from esp.watchlists.models import DatatreeNodeData, Datatree, NoSuchNodeException, NoRootNodeException, models, GetNode, StringToPerm, PermToString
from esp.setup.TreeMap import PopulateInitialDataTree, TreeMap

class TreeTest(TestCase):
    usergrouptree_nodes = []
    sitetree_nodes = []
    
    def setUp(self):
        """ Create a generic basic testing Datatree, with relevant node data """
        for st in TreeMap:
            if 'QualSeriesCategory' in st:
                self.sitetree_nodes.append( st )
            if 'Verb' in st:
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
        numOfRootNodes = Datatree.objects.filter(parent=None,name="ROOT").count()
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

class Test_DatatreeFunctions(TreeTest):
    root = GetNode('')

    def testChildren(self):
        """  Test the 'children()' procedure in Datatree """
        assert self.root.children == Datatree.objects.filter(parent_pk=self.root.id), 'ROOT node\'s children don\t match root.children()'

        # Pick an arbitrary subnode to test
        # I suppose we should care *which* subnode gets tested.  Oh well.
        arbitrary_subnode = self.root.children()[-1]

        assert arbitrary_subnode.children == Datatree.objects.filter(parent_pk=arbitrary_subnode.id)

    def testRefactor(self):
        """ See if all nodes in the tree are still in the tree after a refactor() """
        for node in Datatree.objects.all():
            assert node.is_antecedent(self.root) & self.root.is_descendant(node), 'Node ' + str(node) + ' is not registered in the tree'

        self.root.refactor()
        
        for node in Datatree.objects.all():
            assert node.is_antecedent(self.root) & self.root.is_descendant(node), 'Node ' + str(node) + ' is not registered in the tree, post- refactor()'


watchlistsTestSuite = TestSuite()
watchlistsTestSuite.addTest(OnlyOneRootNode)
watchlistsTestSuite.addTest(AllNodesExist)
watchlistsTestSuite.addTest(Test_DatatreeFunctions)
