from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.storage import LowercaseExtensionStorage


class StorageNormalizationTest(TestCase):
    """Unit tests for lowercasing file extensions."""

    def setUp(self):
        self.storage = LowercaseExtensionStorage()

    def test_normalize_filename_empty(self):
        self.assertEqual(self.storage._normalize_filename(""), "")
        self.assertEqual(self.storage._normalize_filename(None), None)

    def test_normalize_filename_no_extension(self):
        self.assertEqual(self.storage._normalize_filename("README"), "README")

    def test_normalize_filename_lowercases_extension(self):
        self.assertEqual(self.storage._normalize_filename("photo.JPG"), "photo.jpg")
        self.assertEqual(self.storage._normalize_filename("archive.TaR.GZ"), "archive.TaR.gz")

    def test_normalize_filename_with_path(self):
        self.assertEqual(
            self.storage._normalize_filename("images/uploads/photo.PNG"),
            "images/uploads/photo.png",
        )
