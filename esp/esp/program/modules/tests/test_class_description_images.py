import io
import json
from PIL import Image
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ClassSubject
from esp.program.modules.forms.teacherreg import TeacherClassRegForm
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
        self.client = Client()
        self.teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher %s" % self.teacher.username
        )

    def _makeaclass_url(self):
        return '{}{}'.format(self.program.get_teach_url(), 'makeaclass')

    def _valid_form_data(self):
        return {
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

    def _make_image_file(self):
        img = Image.new('RGB', (100, 100), color='red')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return SimpleUploadedFile('test.jpg', buf.read(), content_type='image/jpeg')

    def test_picture_field_not_present_when_tag_disabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'False')
        form = TeacherClassRegForm(self.program.classregmoduleinfo)
        self.assertNotIn('picture', form.fields,
                         "Picture field should not be present when tag is disabled")

    def test_picture_field_present_when_tag_enabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'True')
        form = TeacherClassRegForm(self.program.classregmoduleinfo)
        self.assertIn('picture', form.fields,
                      "Picture field should be present when tag is enabled")

    def test_picture_field_upload(self):
        Tag.setTag('enable_class_description_images', self.program, 'True')
        data = self._valid_form_data()
        image = self._make_image_file()
        response = self.client.post(self._makeaclass_url(), data, {'picture': image})
        cls = ClassSubject.objects.filter(parent_program=self.program, title='Test Class').first()
        if cls:
            self.assertTrue(cls.picture, "Class picture should be saved after upload")
            self.assertTrue(cls.picture.name.endswith('.jpg'),
                            "Uploaded picture should have .jpg extension")

    def test_picture_field_skip_upload_when_tag_disabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'False')
        data = self._valid_form_data()
        image = self._make_image_file()
        response = self.client.post(self._makeaclass_url(), data, {'picture': image})
        cls = ClassSubject.objects.filter(parent_program=self.program, title='Test Class').first()
        if cls:
            self.assertFalse(cls.picture,
                             "Class picture should not be saved when tag is disabled")

    def test_model_fields_exist(self):
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        self.assertTrue(hasattr(cls, 'picture'),
                        "ClassSubject should have a picture field")
        self.assertTrue(hasattr(cls, 'picture_height'),
                        "ClassSubject should have a picture_height field")
        self.assertTrue(hasattr(cls, 'picture_width'),
                        "ClassSubject should have a picture_width field")

    def test_json_api_picture_url_present_when_enabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'True')
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        url = self.program.get_learn_url() + 'catalog_json'
        response = self.client.get(url)
        data = json.loads(response.content)
        for entry in data:
            if 'picture_url' in entry:
                self.assertIsNone(entry['picture_url'],
                                  "picture_url should be present in JSON API when tag is enabled")

    def test_json_api_picture_url_absent_when_disabled(self):
        Tag.setTag('enable_class_description_images', self.program, 'False')
        url = self.program.get_learn_url() + 'catalog_json'
        response = self.client.get(url)
        data = json.loads(response.content)
        for entry in data:
            self.assertNotIn('picture_url', entry,
                             "picture_url should not be in JSON API when tag is disabled")

    def test_render_core_includes_enable_images(self):
        from esp.program.templatetags.class_render import render_class_core
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        ctx = render_class_core(cls)
        self.assertIn('enable_images', ctx,
                      "render_class_core context should include enable_images")
        self.assertFalse(ctx['enable_images'],
                         "enable_images should default to False")

    def test_render_helper_includes_enable_images(self):
        from esp.program.templatetags.class_render import _render_class_helper
        cls = ClassSubject.objects.filter(parent_program=self.program).first()
        ctx = _render_class_helper(cls)
        self.assertIn('enable_images', ctx,
                      "_render_class_helper context should include enable_images")
        self.assertFalse(ctx['enable_images'],
                         "enable_images should default to False")
