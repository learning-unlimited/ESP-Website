from django.test import TestCase
from esp.datatree.models import DataTree
from esp.utils.custom_cache import custom_cache

class DataTree__randwordtest(TestCase):
    def runTest(self):
        assert DataTree.randwordtest(limit=50, quiet=True)

class DataTreeTest(TestCase, custom_cache):
    def setUp(self):
        pass

    def tearDown(self):
        pass
    
    def test_get_by_uri(self):
        """ Test DataTree.get_by_uri() for known corner cases """
        path = "test/get/by/uri/node"

        self.assertEqual(DataTree.objects.filter(uri=path).count(), 0)

        # Test creating some nodes
        node = DataTree.get_by_uri(path, create=True)
        self.assertEqual(DataTree.objects.filter(uri=path).count(), 1)
        self.assertEqual(node.uri, path)

        # Try a child node
        child_path = path + "/child"
        child = DataTree.get_by_uri(child_path, create=True)
        self.assertEqual(DataTree.objects.filter(uri__startswith=path).count(), 2)
        self.assertEqual(child.get_uri(), child_path)

        # Try getting the parent node
        uri_path = "/".join(path.split('/')[:-1])
        uri = DataTree.get_by_uri(uri_path, create=True)
        self.assertEqual(DataTree.objects.filter(uri__startswith=uri_path).count(), 3)
        self.assertEqual(uri.uri, uri_path)

        # Try renaming a node:
        uri.name = "uri2"
        uri.save()

        # Make sure the URI's of the child nodes are updated
        self.assertEqual(DataTree.get_by_uri("test/get/by/uri2", create=True).get_uri(), "test/get/by/uri2")
        self.assertEqual(DataTree.get_by_uri("test/get/by/uri2/node", create=True).get_uri(), "test/get/by/uri2/node")
        self.assertEqual(DataTree.get_by_uri("test/get/by/uri2/node/child", create=True).get_uri(), "test/get/by/uri2/node/child")

        # Try deleting a node; make sure it goes away
        child.delete()
        try:
            node = DataTree.get_by_uri("test/get/by/uri2/node/child")
        except DataTree.DoesNotExist:
            node = None

        self.assertEqual(node, None)
