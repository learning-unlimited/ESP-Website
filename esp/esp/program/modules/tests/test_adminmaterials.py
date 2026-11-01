"""
Behavioral tests for AdminMaterials (esp/program/modules/handlers/adminmaterials.py).

Covers the three POST commands on get_materials(): add / rename / delete,
plus permission gating.
"""

from django.core.files.uploadedfile import SimpleUploadedFile

from esp.program.models import ClassSubject, Program
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.qsdmedia.models import Media


class AdminMaterialsTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.url = self.get_module_url("manage", "get_materials")
        self.cls = ClassSubject.objects.filter(parent_program=self.program).first()

    def _upload_payload(self, target_id, title="Test doc", filename="handout.pdf"):
        return {
            "command": "add",
            "title": title,
            "target_obj": str(target_id),
            "uploadedfile": SimpleUploadedFile(
                filename, b"%PDF-1.4 fake content", content_type="application/pdf"
            ),
        }

    def test_admin_get_returns_200(self):
        self.login_as("admin")
        response = self.assert_view_ok(self.url)
        self.assertIn("uploadform", response.context)
        self.assertIn("renameform", response.context)

    def test_student_get_is_forbidden(self):
        self.login_as("student")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "errors/program/notanadmin.html")

    def test_add_with_class_prefixes_filename_and_links_class(self):
        """add with a class target prefixes emailcode and sets owner to the class."""
        self.login_as("admin")
        response = self.client.post(
            self.url, self._upload_payload(self.cls.id, filename="waiver.pdf")
        )
        self.assertEqual(response.status_code, 200)
        media = Media.objects.filter(friendly_name="Test doc").first()
        self.assertIsNotNone(media, "add should create a Media object")
        self.assertEqual(
            media.file_name,
            f"{self.cls.emailcode()}_waiver.pdf",
            "uploaded file should be stored, got %r" % (media.file_name,),
        )
        # Owner should be the class (GenericForeignKey resolves to ClassSubject)
        self.assertEqual(media.owner, self.cls)

    def test_add_to_program_sets_program_owner(self):
        """add with target 0 assigns the program as owner (no class prefix)."""
        self.login_as("admin")
        self.client.post(
            self.url,
            self._upload_payload(0, title="Program doc", filename="program.pdf"),
        )
        media = Media.objects.filter(friendly_name="Program doc").first()
        self.assertIsNotNone(media)
        self.assertEqual(media.owner, self.program)

    def test_rename_updates_friendly_name(self):
        self.login_as("admin")
        self.client.post(
            self.url, self._upload_payload(self.cls.id, title="Before rename")
        )
        media = Media.objects.filter(friendly_name="Before rename").first()
        self.assertIsNotNone(media)
        response = self.client.post(
            self.url,
            {
                "command": "rename",
                "docid": str(media.id),
                "title": "After rename",
            },
        )
        self.assertEqual(response.status_code, 200)
        media.refresh_from_db()
        self.assertEqual(media.friendly_name, "After rename")

    def test_delete_removes_media(self):
        self.login_as("admin")
        self.client.post(
            self.url, self._upload_payload(self.cls.id, title="To delete")
        )
        media = Media.objects.filter(friendly_name="To delete").first()
        self.assertIsNotNone(media)
        media_id = media.id
        response = self.client.post(
            self.url, {"command": "delete", "docid": str(media_id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Media.objects.filter(id=media_id).exists())

    def test_delete_other_program_media_fails(self):
        """Admin cannot delete a document belonging to another program."""
        other_prog = Program.objects.create(
            url="TestProgram/2020_Other",
            name="TestProgram Other 2020",
            grade_min=7,
            grade_max=12,
            director_email="info@test.learningu.org",
            program_size_max=3000,
        )
        other_media = Media.objects.create(
            friendly_name="Other Program Doc",
            owner=other_prog,
        )
        self.login_as("admin")
        response = self.client.post(
            self.url, {"command": "delete", "docid": str(other_media.id)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Media.objects.filter(id=other_media.id).exists())

    def test_rename_other_program_media_fails(self):
        """Admin cannot rename a document belonging to another program."""
        other_prog = Program.objects.create(
            url="TestProgram/2021_Other",
            name="TestProgram Other 2021",
            grade_min=7,
            grade_max=12,
            director_email="info@test.learningu.org",
            program_size_max=3000,
        )
        other_media = Media.objects.create(
            friendly_name="Original Name",
            owner=other_prog,
        )
        self.login_as("admin")
        response = self.client.post(
            self.url,
            {
                "command": "rename",
                "docid": str(other_media.id),
                "title": "Hacked Name",
            },
        )
        self.assertEqual(response.status_code, 200)
        other_media.refresh_from_db()
        self.assertEqual(other_media.friendly_name, "Original Name")

    def test_delete_and_rename_invalid_docid_does_not_crash(self):
        """Invalid, out-of-range, non-existent, or empty docid should not crash."""
        self.login_as("admin")
        for bad_id in ["invalid", "999999", "99999999999999999999", "", None]:
            data_del = {"command": "delete"}
            if bad_id is not None:
                data_del["docid"] = bad_id
            response = self.client.post(self.url, data_del)
            self.assertEqual(response.status_code, 200)

            data_rename = {"command": "rename", "title": "New Title"}
            if bad_id is not None:
                data_rename["docid"] = bad_id
            response = self.client.post(self.url, data_rename)
            self.assertEqual(response.status_code, 200)

    def test_missing_or_invalid_command_does_not_crash(self):
        """POST request without a command or with an unknown command should not crash."""
        self.login_as("admin")
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.url, {"command": "unknown"})
        self.assertEqual(response.status_code, 200)
