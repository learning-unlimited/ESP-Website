"""
Unit tests for:
  - esp/web/storage.py          (LowercaseExtensionStorage)
  - esp/web/forms/__init__.py   (ResizeImageField)
  - esp/web/forms/bioedit_form.py  (BioEditForm)
  - esp/web/forms/fileupload_form.py (FileUploadForm, FileUploadForm_Admin, FileRenameForm)

PR 2/11 — web module coverage improvement
"""

from unittest.mock import patch, MagicMock

from django import forms
from django.core.files.storage import FileSystemStorage
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
    """Tests for LowercaseExtensionStorage.save()

    Copilot fix: use patch.object(FileSystemStorage, ...) directly instead of
    fragile __bases__[0] inheritance-chain access.
    """

    def setUp(self):
        self.storage = LowercaseExtensionStorage()

    def test_save_lowercases_extension(self):
        content = SimpleUploadedFile("test.JPG", b"fake-image-data")
        with patch.object(FileSystemStorage, "save", return_value="test.jpg") as mock_save:
            self.storage.save("test.JPG", content)
            call_args = mock_save.call_args[0]
            self.assertEqual(call_args[0], "test.jpg")

    def test_save_passes_content_unchanged(self):
        content = SimpleUploadedFile("photo.PNG", b"fake-png-data")
        with patch.object(FileSystemStorage, "save", return_value="photo.png") as mock_save:
            self.storage.save("photo.PNG", content)
            call_args = mock_save.call_args[0]
            self.assertEqual(call_args[1], content)

    def test_save_no_extension_passes_name_unchanged(self):
        content = SimpleUploadedFile("README", b"data")
        with patch.object(FileSystemStorage, "save", return_value="README") as mock_save:
            self.storage.save("README", content)
            call_args = mock_save.call_args[0]
            self.assertEqual(call_args[0], "README")


# ---------------------------------------------------------------------------
# ResizeImageField — __init__
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
        result = field.clean(None, initial=None)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# ResizeImageField — clean() branches (100 % coverage for forms/__init__.py)
# ---------------------------------------------------------------------------

class ResizeImageFieldCleanTest(TestCase):
    """Tests for ResizeImageField.clean() — every branch exercised."""

    def _mock_pil_image(self):
        """PIL Image mock that writes fake bytes to the buffer on save()."""
        img = MagicMock()
        img.format = 'JPEG'
        img.save.side_effect = lambda buf, fmt: buf.write(b'\xff\xd8\xff')
        return img

    def test_returns_file_unchanged_when_size_is_none(self):
        """size=None skips the resize block entirely — file returned as-is."""
        fake = SimpleUploadedFile("shot.jpg", b"data")
        field = ResizeImageField(size=None, required=False)
        with patch.object(forms.FileField, 'clean', return_value=fake):
            result = field.clean(fake, initial=None)
        self.assertIs(result, fake)

    def test_resize_via_read_attribute(self):
        """File has .read — BytesIO branch taken; extension is lowercased."""
        fake = SimpleUploadedFile("shot.JPG", b"data")
        field = ResizeImageField(size=(100, 100), required=False)
        mock_img = self._mock_pil_image()
        with patch.object(forms.FileField, 'clean', return_value=fake), \
             patch('PIL.Image.open', return_value=mock_img), \
             patch('PIL.Image.ANTIALIAS', new=1, create=True):
            result = field.clean(fake, initial=None)
        self.assertIsInstance(result, SimpleUploadedFile)
        self.assertTrue(result.name.endswith('.jpg'))   # extension lowercased

    def test_resize_via_temporary_file_path(self):
        """File has .temporary_file_path — path string passed to Image.open."""
        fake = MagicMock()
        fake.name = "upload.JPG"
        fake.temporary_file_path.return_value = "/tmp/upload.JPG"
        field = ResizeImageField(size=(100, 100), required=False)
        mock_img = self._mock_pil_image()
        with patch.object(forms.FileField, 'clean', return_value=fake), \
             patch('PIL.Image.open', return_value=mock_img) as mock_open, \
             patch('PIL.Image.ANTIALIAS', new=1, create=True):
            field.clean(fake, initial=None)
        mock_open.assert_called_once_with("/tmp/upload.JPG")

    def test_unreadable_file_raises_validation_error(self):
        """Neither .read nor .temporary_file_path — raises ValidationError."""
        fake = MagicMock(spec=['name'])   # only .name — no read or temp_file_path
        fake.name = "mystery.jpg"
        field = ResizeImageField(size=(100, 100), required=False)
        with patch.object(forms.FileField, 'clean', return_value=fake):
            with self.assertRaises(forms.ValidationError) as ctx:
                field.clean(fake, initial=None)
        self.assertIn('Image unreadable', str(ctx.exception))

    def test_ioerror_in_pil_raises_validation_error(self):
        """IOError during Image.open — raises ValidationError('Image resize failed.')."""
        fake = SimpleUploadedFile("shot.jpg", b"data")
        field = ResizeImageField(size=(100, 100), required=False)
        with patch.object(forms.FileField, 'clean', return_value=fake), \
             patch('PIL.Image.open', side_effect=IOError("corrupt")), \
             patch('PIL.Image.ANTIALIAS', new=1, create=True):
            with self.assertRaises(forms.ValidationError) as ctx:
                field.clean(fake, initial=None)
        self.assertIn('Image resize failed', str(ctx.exception))


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
        form = BioEditForm(data={'slugbio': 'x' * 51})  # max_length=50
        self.assertFalse(form.is_valid())
        self.assertIn('slugbio', form.errors)

    def test_slugbio_at_max_length_valid(self):
        form = BioEditForm(data={'slugbio': 'x' * 50})
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
