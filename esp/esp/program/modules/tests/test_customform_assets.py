import json

from esp.customforms.DynamicModel import DynamicModelHandler
from esp.customforms.models import Form
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser

CUSTOM_FORM_ASSETS = (
    'customforms-form.css',
    'jquery.validate.min.js',
    'additional-methods.min.js',
    'customforms-validation.js',
    'qtip.js',
)


class CustomFormAssetsTest(ProgramFrameworkTest):
    """Custom form pages load the custom form stylesheet and scripts once,
    including module pages whose template overrides the content block."""

    def setUp(self):
        super().setUp()
        admin, _ = ESPUser.objects.get_or_create(username='cfadmin')
        admin.set_password('password')
        admin.save()
        admin.makeAdmin()
        self.client.login(username='cfadmin', password='password')
        form_data = {
            'title': 'Asset Test Form', 'perms': '', 'link_id': -1, 'link_type': '-1',
            'success_url': '/formsuccess.html', 'success_message': 'Thank you!',
            'anonymous': False, 'desc': 'Test',
            'pages': [{'parent_id': -1, 'seq': 0, 'sections': [{
                'data': {'help_text': '', 'question_text': '', 'seq': 0},
                'fields': [{'data': {'field_type': 'textField', 'question_text': 'Name', 'seq': 0,
                                     'required': True, 'parent_id': -1, 'help_text': 'Your name',
                                     'attrs': {'correct_answer': '', 'charlimits': ','}}}],
            }]}],
        }
        self.client.post('/customforms/submit/', json.dumps(form_data), content_type='application/json',
                         HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.form = Form.objects.get(title='Asset Test Form')
        Tag.setTag(key='teach_extraform_id', value=self.form.id, target=self.program)
        self.client.logout()

    def tearDown(self):
        Tag.unSetTag(key='teach_extraform_id', target=self.program)
        DynamicModelHandler(self.form).purgeDynModel()
        super().tearDown()

    def _assert_assets_once(self, response):
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        for asset in CUSTOM_FORM_ASSETS:
            self.assertEqual(content.count(asset), 1, asset)

    def test_standalone_form_page(self):
        self.client.login(username=self.teachers[0].username, password='password')
        self._assert_assets_once(self.client.get('/customforms/view/%s/' % self.form.id))

    def test_teacher_module_form_page(self):
        self.client.login(username=self.teachers[0].username, password='password')
        self._assert_assets_once(self.client.get('/teach/%s/extraform' % self.program.url))
