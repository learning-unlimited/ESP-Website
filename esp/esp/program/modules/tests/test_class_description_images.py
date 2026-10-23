import io
import json
import shutil
import tempfile

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from esp.program.class_status import ClassStatus
from esp.program.models import ClassSubject
from esp.program.modules.forms.teacherreg import TeacherClassRegForm
from esp.program.templatetags.class_render import render_class_core
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag


class ClassDescriptionImagesTest(ProgramFrameworkTest):
    """Tests for the class description images feature."""

    DEFAULT_SETTINGS = {
        'num_timeslots': 3,
        'timeslot_length': 50,
        'timeslot_gap': 10,
        'room_capacity': 30,
        'num_categories': 2,
        'num_rooms': 2,
        'num_teachers': 3,
        'classes_per_teacher': 1,
        'sections_per_class': 1,
        'num_students': 2,
        'num_admins': 1,
        'program_type': 'TestProgram',
        'program_instance_name': '2222_Summer',
        'program_instance_label': 'Summer 2222',
    }

    def setUp(self):
        super(ClassDescriptionImagesTest, self).setUp(**self.DEFAULT_SETTINGS)
        # Keep uploaded test images out of the real media directory
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)

        Tag.setTag('enable_class_description_images', self.program, 'True')
        self.client = Client()
        self.teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher %s" % self.teacher.username
        )
        ClassSubject.objects.filter(parent_program=self.program, teachers=self.teacher).delete()

    def _teach_url(self, extra):
        return '{}{}'.format(self.program.get_teach_url(), extra)

    def _form_data(self, **extra):
        data = {
            'title': 'Test Class',
            'category': self.categories[0].id,
            'class_info': 'A description.',
            'prereqs': '',
            'duration': self.program.getDurations()[0][0],
            'num_sections': '1',
            'session_count': '1',
            'grade_min': self.program.grade_min,
            'grade_max': self.program.grade_max,
            'class_size_max': '20',
            'allow_lateness': 'False',
            'message_for_directors': '',
            'class_reg_page': '1',
            'hardness_rating': '**',
            'request-TOTAL_FORMS': '0',
            'request-INITIAL_FORMS': '0',
            'request-MAX_NUM_FORMS': '1000',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
            'restype-MAX_NUM_FORMS': '1000',
        }
        data.update(extra)
        return data

    def _make_image_file(self, size=(800, 600)):
        buf = io.BytesIO()
        Image.new('RGB', size, color='red').save(buf, format='PNG')
        return SimpleUploadedFile('test.png', buf.getvalue(), content_type='image/png')

    def _teacher_classes(self):
        return ClassSubject.objects.filter(parent_program=self.program, teachers=self.teacher)

    def _create_class_with_picture(self):
        self.client.post(self._teach_url('makeaclass'), self._form_data(picture=self._make_image_file()))
        cls = self._teacher_classes().get()
        self.assertTrue(cls.picture, "Class picture should be saved after upload")
        return cls

    def test_picture_field_absent_when_tag_disabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'False')
        form = TeacherClassRegForm(self.program.classregmoduleinfo)
        self.assertNotIn('picture', form.fields)

    def test_picture_field_follows_description_when_tag_enabled(self):
        names = list(TeacherClassRegForm(self.program.classregmoduleinfo).fields)
        self.assertEqual(names[names.index('class_info') + 1], 'picture')

    def test_upload_saves_resized_picture(self):
        cls = self._create_class_with_picture()
        self.assertTrue(cls.picture.name.startswith('uploaded/class_pictures/'))
        self.assertEqual((cls.picture_width, cls.picture_height), (500, 375))

    def test_upload_ignored_when_tag_disabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'False')
        self.client.post(self._teach_url('makeaclass'), self._form_data(picture=self._make_image_file()))
        self.assertFalse(self._teacher_classes().get().picture)

    def test_invalid_upload_rejected(self):
        not_an_image = SimpleUploadedFile('test.png', b'not an image', content_type='image/png')
        response = self.client.post(self._teach_url('makeaclass'), self._form_data(picture=not_an_image))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self._teacher_classes().exists())

    def test_edit_form_shows_current_picture(self):
        cls = self._create_class_with_picture()
        response = self.client.get(self._teach_url('editclass/%d' % cls.id))
        self.assertContains(response, cls.picture.url)

    def test_edit_without_upload_keeps_picture(self):
        cls = self._create_class_with_picture()
        old_name = cls.picture.name
        self.client.post(self._teach_url('editclass/%d' % cls.id), self._form_data(title='Renamed Class'))
        cls.refresh_from_db()
        self.assertEqual(cls.title, 'Renamed Class')
        self.assertEqual(cls.picture.name, old_name)

    def test_edit_with_clear_removes_picture(self):
        cls = self._create_class_with_picture()
        self.client.post(self._teach_url('editclass/%d' % cls.id), self._form_data(**{'picture-clear': 'on'}))
        cls.refresh_from_db()
        self.assertFalse(cls.picture)
        self.assertIsNone(cls.picture_width)

    def test_draft_keeps_picture_through_submit(self):
        self.client.post(self._teach_url('makeaclass'),
                         self._form_data(picture=self._make_image_file(), save_action='draft'))
        draft = self._teacher_classes().get()
        self.assertEqual(draft.status, ClassStatus.DRAFT)
        self.assertTrue(draft.picture, "Draft should keep the uploaded picture")

        self.client.post(self._teach_url('makeaclass'), self._form_data(class_id=draft.id))
        draft.refresh_from_db()
        self.assertEqual(draft.status, ClassStatus.UNREVIEWED)
        self.assertTrue(draft.picture, "Submitting a draft should keep its picture")

    def test_draft_with_invalid_upload_saves_without_picture(self):
        not_an_image = SimpleUploadedFile('test.png', b'not an image', content_type='image/png')
        self.client.post(self._teach_url('makeaclass'),
                         self._form_data(picture=not_an_image, save_action='draft'))
        draft = self._teacher_classes().get()
        self.assertEqual(draft.status, ClassStatus.DRAFT)
        self.assertFalse(draft.picture)

    def _catalog_json_classes(self):
        response = self.client.get('/json/%s/class_subjects/catalog' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        return {c['id']: c for c in json.loads(response.content)['classes']}

    def test_catalog_json_picture_url_when_enabled(self):
        cls = self._create_class_with_picture()
        classes = self._catalog_json_classes()
        self.assertEqual(classes[cls.id]['picture_url'], cls.picture.url)
        other = ClassSubject.objects.filter(parent_program=self.program).exclude(id=cls.id).first()
        self.assertIsNone(classes[other.id]['picture_url'])

    def test_catalog_json_omits_picture_url_when_disabled(self):
        cls = self._create_class_with_picture()
        Tag.setTag('enable_class_description_images', self.program, 'False')
        self.assertNotIn('picture_url', self._catalog_json_classes()[cls.id])

    def test_render_class_core_follows_tag(self):
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        self.assertTrue(render_class_core(cls)['enable_images'])
        Tag.setTag('enable_class_description_images', self.program, 'False')
        self.assertFalse(render_class_core(cls)['enable_images'],
                         "Changing the tag should invalidate the cached catalog context")
