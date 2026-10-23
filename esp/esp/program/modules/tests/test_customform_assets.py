import json
import re

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
# Browsers block a CDN script whose integrity hash doesn't match the file.
JQUERY_VALIDATE_SRI = {
    'jquery.validate.min.js': 'sha512-rstIgDs0xPgmG6RX1Aba4KV5cWJbAMcvRCVmglpam9SoHZiUCyQVDdH2LPlxoHtrv17XWblE/V/PP+Tr04hbtA==',
    'additional-methods.min.js': 'sha512-6S5LYNn3ZJCIm0f9L6BCerqFlQ4f5MwNKq+EthDXabtaJvg3TuFLhpno9pcm+5Ynm6jdA9xfpQoMz2fcjVMk9g==',
}


class CustomFormAssetsTest(ProgramFrameworkTest):
    """Custom form pages load the custom form stylesheet and scripts once,
    including module pages whose template overrides the content block, and
    put the Next button before the navigation buttons."""

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
            'pages': [{'parent_id': -1, 'seq': seq, 'sections': [{
                'data': {'help_text': '', 'question_text': '', 'seq': 0},
                'fields': [{'data': {'field_type': 'textField', 'question_text': label, 'seq': 0,
                                     'required': True, 'parent_id': -1, 'help_text': label,
                                     'attrs': {'correct_answer': '', 'charlimits': ','}}}],
            }]} for seq, label in enumerate(['Name', 'School'])],
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
        for asset, integrity in JQUERY_VALIDATE_SRI.items():
            self.assertIn('src="https://cdnjs.cloudflare.com/ajax/libs/jquery-validate/1.19.5/%s" integrity="%s"'
                          % (asset, integrity), content)

    def test_standalone_form_page(self):
        self.client.login(username=self.teachers[0].username, password='password')
        self._assert_assets_once(self.client.get('/customforms/view/%s/' % self.form.id))

    def test_teacher_module_form_page(self):
        self.client.login(username=self.teachers[0].username, password='password')
        self._assert_assets_once(self.client.get('/teach/%s/extraform' % self.program.url))

    def test_teacher_module_form_uses_client_validation(self):
        """customforms-validation.js attaches to #cstform, so the module form needs that id."""
        self.client.login(username=self.teachers[0].username, password='password')
        response = self.client.get('/teach/%s/extraform' % self.program.url)
        self.assertContains(response, 'id="cstform"', count=1)

    def _assert_enter_submits_next(self, url):
        """On the second page, the submit button comes before Prev Step, since
        pressing Enter submits the form with its first submit button."""
        content = self.client.get(url).content.decode()
        prefix = re.search(r'name="([\w-]+)-current_step"', content).group(1)
        name = self.form.field_set.get(label='Name')
        response = self.client.post(url, {'%s-current_step' % prefix: '0', 'question_%d' % name.id: 'Ann'})
        content = response.content.decode()
        self.assertIn('Step 2 of 2', content)
        form = content[content.index('class="form-stacked"'):]
        self.assertLess(form.index('type="submit"'), form.index('Prev Step'))

    def test_standalone_form_enter_submits_next(self):
        self.client.login(username=self.teachers[0].username, password='password')
        self._assert_enter_submits_next('/customforms/view/%s/' % self.form.id)

    def test_teacher_module_form_enter_submits_next(self):
        self.client.login(username=self.teachers[0].username, password='password')
        self._assert_enter_submits_next('/teach/%s/extraform' % self.program.url)
