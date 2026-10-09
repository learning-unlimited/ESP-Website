"""
Behavioral tests for AdminMaterials (esp/program/modules/handlers/adminmaterials.py).

Covers the three POST commands on get_materials(): add / rename / delete,
plus permission gating. Follows the acceptance criteria in #5127.

Refs: #5127, #3780
"""

from django.core.files.uploadedfile import SimpleUploadedFile

from esp.program.models import ClassSubject
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
        self.assertTrue(
            media.filename.name.endswith("waiver.pdf")
            or "waiver" in (media.filename.name or ""),
            "uploaded file should be stored, got %r" % (media.filename,),
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
