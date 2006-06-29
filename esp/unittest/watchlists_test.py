from esp.unittest.unittest import TestCase, TestSuite
from esp.watchlists.models import Category, Subscription, DatatreeNodeData, Datatree, NoSuchNodeException, NoRootNodeException, models, GetNode

class TreeTest(TestCase):
    usergrouptree_nodes = (
        'UserGroupTree/Users/Admins/Gods',
        'UserGroupTree/Users/Admins',
        'UserGroupTree/Users/Teachers',
        'UserGroupTree/Users/Students',
        'UserGroupTree/Registrar/ClassReg',
        )

    sitetree_nodes = (
        'SiteTree/Classes',
        'SiteTree/Programs/Splash/2006/Classes/SPAM/Documents/Homework/Page1/Paragraph2/Sentence5/Word3/Character1',
        'SiteTree/Classes/ChooseYourOwnAdventure',
        )
    
    def setUp(self):
        """ Create a generic basic testing Datatree, with relevant node data """
        models.PopulateInitialDataTree()

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
        numOfRootNodes = Datatree.objects.filter(parent=NONE,name="ROOT").count()
        assert numOfRootNodes == 1, 'There can only be one ROOT node.  There are ' + str(numOfRootNodes) + '.'
        
class AllNodesExist(TreeTest):
    def runTest(self):
        """ Do all the sample nodes in TreeTest exist? """
        # Hack to get the root node easily; this isn't currently defined behavhior
        # (maybe it should be?)
        root = GetNode('')

        for node in self.nodes:
            # Raises a NoSuchNodeException if the node doesn't exist
            root.tree_decode(node)

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
