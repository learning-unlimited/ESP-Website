from esp.program.tests import ProgramFrameworkTest
from django.test import override_settings

@override_settings(
    TWILIO_ACCOUNT_SID='ACmock',
    TWILIO_AUTH_TOKEN='mocktoken',
    TWILIO_ACCOUNT_NUMBERS=['+15555555555']
)
class UserSearchErrorHandlingTest(ProgramFrameworkTest):
    def setUp(self):
        super(UserSearchErrorHandlingTest, self).setUp()
        self.client.login(username=self.admins[0].username, password='password')

    def test_listgen_selectlist_error(self):
        url = f'/manage/{self.program.url}/selectList'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_batchclassreg_error(self):
        url = f'/manage/{self.program.url}/batchclassreg'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_commpanel_error(self):
        url = f'/manage/{self.program.url}/commpanel'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_deactivate_error(self):
        url = f'/manage/{self.program.url}/deactivate'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_grouptextpanel_error(self):
        url = f'/manage/{self.program.url}/grouptextpanel'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_usermap_error(self):
        url = f'/manage/{self.program.url}/usermap'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_generatetags_error(self):
        url = f'/manage/{self.program.url}/generatetags'
        response = self.client.post(url, {
            'type': 'aul',
            'blanktitle': 'Student',
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
            'progname': 'TestProgram',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_usergroup_error(self):
        url = f'/manage/{self.program.url}/usergroup'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)

    def test_userrecords_error(self):
        url = f'/manage/{self.program.url}/userrecords'
        response = self.client.post(url, {
            'recipient_type': 'Student',
            'base_list': 'all_Student',
            'userid': 'abc',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error:', response.content)
        self.assertIn(b'User id invalid', response.content)
