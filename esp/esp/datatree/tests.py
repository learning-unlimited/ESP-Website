from django.test import TestCase
from esp.datatree.models import DataTree

class DataTree__randwordtest(TestCase):
    def runTest(self):
        DataTree.randwordtest(limit=50)
