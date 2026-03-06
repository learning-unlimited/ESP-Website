"""
Unit tests for:
  - esp/web/storage.py          (LowercaseExtensionStorage)
  - esp/web/forms/__init__.py   (ResizeImageField)
  - esp/web/forms/contact_form.py  (ContactForm)
  - esp/web/forms/bioedit_form.py  (BioEditForm)
  - esp/web/forms/fileupload_form.py (FileUploadForm, FileUploadForm_Admin, FileRenameForm)

PR 2/6 — web module coverage improvement
"""

import io
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from esp.web.storage import LowercaseExtensionStorage
from esp.web.forms import ResizeImageField
from esp.web.forms.bioedit_form import BioEditForm
from esp.web.forms.fileupload_form import (
    FileUploadForm,
    FileUploadForm_Admin,
    FileRenameForm,
)


# ---------------------------------------------------------------------------
# LowercaseExtensionStorage
# ---------------------------------------------------------------------------

class LowercaseExtensionStorageNormalizeTest(TestCase):
    """Tests for LowercaseExtensionStorage._normalize_filename()"""

    def setUp(self):
        self.storage = LowercaseExtensionStorage()

    def test_uppercase_jpg_lowercased(self):
        self.assertEqual(self.storage._normalize_filename("photo.JPG"), "photo.jpg")

    def test_uppercase_png_lowercased(self):
        self.assertEqual(self.storage._normalize_filename("image.PNG"), "image.png")

    def test_mixed_case_extension_lowercased(self):
        self.assertEqual(self.storage._normalize_filename("file.JpEg"), "file.jpeg")

    def test_already_lowercase_unchanged(self):
        self.assertEqual(self.storage._normalize_filename("photo.jpg"), "photo.jpg")

    def test_no_extension_unchanged(self):
        self.assertEqual(self.storage._normalize_filename("README"), "README")

    def test_empty_string_returned_as_is(self):
        self.assertEqual(self.storage._normalize_filename(""), "")

    def test_none_returned_as_is(self):
        self.assertIsNone(self.storage._normalize_filename(None))

    def test_path_with_directories_preserves_dirs(self):
        result = self.storage._normalize_filename("uploads/photos/avatar.JPG")
        self.assertEqual(result, "uploads/photos/avatar.jpg")

    def test_path_with_nested_dirs(self):
        result = self.storage._normalize_filename("a/b/c/file.PNG")
        self.assertEqual(result, "a/b/c/file.png")

    def test_basename_case_preserved(self):
        # Only the extension is lowercased, not the basename
        result = self.storage._normalize_filename("MyPhoto.JPG")
        self.assertEqual(result, "MyPhoto.jpg")

    def test_dot_in_directory_name(self):
        result = self.storage._normalize_filename("my.dir/file.TXT")
        self.assertEqual(result, "my.dir/file.txt")


class LowercaseExtensionStorageSaveTest(TestCase):
    """Tests for LowercaseExtensionStorage.save()"""

    def setUp(self):
        self.storage = LowercaseExtensionStorage()

    def test_save_lowercases_extension(self):
        content = SimpleUploadedFile("test.JPG", b"fake-image-data")
        with patch.object(
            LowercaseExtensionStorage.__bases__[0],
            "save",
            return_value="test.jpg"
        ) as mock_save:
            result = self.storage.save("test.JPG", content)
            # The name passed to parent must be lowercased
            call_args = mock_save.call_args[0]
            self.assertEqual(call_args[0], "test.jpg")

    def test_save_passes_content_unchanged(self):
        content = SimpleUploadedFile("photo.PNG", b"fake-png-data")
        with patch.object(
            LowercaseExtensionStorage.__bases__[0],
            "save",
            return_value="photo.png"
        ) as mock_save:
            self.storage.save("photo.PNG", content)
            call_args = mock_save.call_args[0]
            self.assertEqual(call_args[1], content)

    def test_save_no_extension_passes_name_unchanged(self):
        content = SimpleUploadedFile("README", b"data")
        with patch.object(
            LowercaseExtensionStorage.__bases__[0],
            "save",
            return_value="README"
        ) as mock_save:
            self.storage.save("README", content)
            call_args = mock_save.call_args[0]
            self.assertEqual(call_args[0], "README")


# ---------------------------------------------------------------------------
# ResizeImageField
# ---------------------------------------------------------------------------

class ResizeImageFieldInitTest(TestCase):
    """Tests for ResizeImageField.__init__()"""

    def test_size_stored(self):
        field = ResizeImageField(size=(300, 300), required=False)
        self.assertEqual(field.size, (300, 300))

    def test_no_size_defaults_to_none(self):
        field = ResizeImageField(required=False)
        self.assertIsNone(field.size)

    def test_not_required_accepts_empty(self):
        field = ResizeImageField(required=False)
        # clean(None, initial=None) on a non-required field should return None
        result = field.clean(None, initial=None)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# BioEditForm
# ---------------------------------------------------------------------------

class BioEditFormTest(TestCase):
    """Tests for BioEditForm"""

    def test_empty_form_is_valid(self):
        # All fields are optional
        form = BioEditForm(data={})
        self.assertTrue(form.is_valid(), form.errors)

    def test_with_slugbio_and_bio(self):
        form = BioEditForm(data={
            'slugbio': 'Math enthusiast',
            'bio': 'I love teaching algebra.',
            'hidden': False,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_slugbio_max_length_enforced(self):
        form = BioEditForm(data={
            'slugbio': 'x' * 51,  # max_length=50
        })
        self.assertFalse(form.is_valid())
        self.assertIn('slugbio', form.errors)

    def test_slugbio_at_max_length_valid(self):
        form = BioEditForm(data={
            'slugbio': 'x' * 50,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_hidden_field_false(self):
        form = BioEditForm(data={'hidden': False})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data['hidden'])

    def test_hidden_field_true(self):
        form = BioEditForm(data={'hidden': True})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data['hidden'])

    def test_picture_not_required(self):
        # No picture submitted — should still be valid
        form = BioEditForm(data={'bio': 'Some bio text'}, files={})
        self.assertTrue(form.is_valid(), form.errors)

    def test_bio_field_not_required(self):
        form = BioEditForm(data={'bio': ''})
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# FileUploadForm
# ---------------------------------------------------------------------------

class FileUploadFormTest(TestCase):
    """Tests for FileUploadForm"""

    def _make_file(self, name="test.pdf", content=b"data"):
        return SimpleUploadedFile(name, content)

    def test_valid_submission(self):
        form = FileUploadForm(
            data={'title': 'My Document'},
            files={'uploadedfile': self._make_file()},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_title_invalid(self):
        form = FileUploadForm(
            data={},
            files={'uploadedfile': self._make_file()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_missing_file_invalid(self):
        form = FileUploadForm(
            data={'title': 'My Document'},
            files={},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('uploadedfile', form.errors)

    def test_both_missing_invalid(self):
        form = FileUploadForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('uploadedfile', form.errors)


# ---------------------------------------------------------------------------
# FileUploadForm_Admin
# ---------------------------------------------------------------------------

class FileUploadFormAdminTest(TestCase):
    """Tests for FileUploadForm_Admin"""

    def _make_file(self, name="doc.txt", content=b"data"):
        return SimpleUploadedFile(name, content)

    def test_set_choices_updates_field(self):
        form = FileUploadForm_Admin(
            data={'title': 'T', 'target_obj': 'a'},
            files={'uploadedfile': self._make_file()},
        )
        choices = [('a', 'Option A'), ('b', 'Option B')]
        form.set_choices(choices)
        self.assertEqual(
            list(form.fields['target_obj'].choices),
            choices,
        )

    def test_valid_after_set_choices(self):
        choices = [('a', 'Option A'), ('b', 'Option B')]
        form = FileUploadForm_Admin(
            data={'title': 'Doc', 'target_obj': 'a'},
            files={'uploadedfile': self._make_file()},
        )
        form.set_choices(choices)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_title_invalid(self):
        form = FileUploadForm_Admin(
            data={'target_obj': 'a'},
            files={'uploadedfile': self._make_file()},
        )
        form.set_choices([('a', 'A')])
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_missing_file_invalid(self):
        form = FileUploadForm_Admin(
            data={'title': 'Doc', 'target_obj': 'a'},
            files={},
        )
        form.set_choices([('a', 'A')])
        self.assertFalse(form.is_valid())
        self.assertIn('uploadedfile', form.errors)


# ---------------------------------------------------------------------------
# FileRenameForm
# ---------------------------------------------------------------------------

class FileRenameFormTest(TestCase):
    """Tests for FileRenameForm"""

    def test_valid_with_title(self):
        form = FileRenameForm(data={'title': 'new_name'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_title_invalid(self):
        form = FileRenameForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_empty_title_invalid(self):
        form = FileRenameForm(data={'title': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
