"""Endpoints given missing or bad input answer with an error response instead of crashing."""

from esp.program.tests import ProgramFrameworkTest

ERROR_LOGGER = 'esp.middleware.esperrormiddleware'


class EndpointInputErrorTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.url_base = self.program.getUrlBase()

    def test_set_donation_amount_is_gone(self):
        self.client.login(username=self.students[0].username, password='password')
        response = self.client.get(f'/json/{self.url_base}/set_donation_amount')
        self.assertEqual(response.status_code, 404)

    def test_qsd_preview_checks_login_before_reading_data(self):
        self.assertEqual(self.client.get('/admin/ajax_qsd_preview').status_code, 401)
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post('/admin/ajax_qsd_preview', {'url': 'test_page'})
        self.assertEqual(response.status_code, 400)

    def test_change_log_needs_a_numeric_index(self):
        self.client.login(username=self.admin.username, password='password')
        url = f'/manage/{self.url_base}/ajax_change_log'
        for params in ({}, {'last_fetched_index': 'abc'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(url, params).status_code, 400)
        self.assertEqual(self.client.get(url, {'last_fetched_index': 0}).status_code, 200)

    def test_class_detail_without_a_class_is_not_found(self):
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get(f'/onsite/{self.url_base}/ajaxclassdetail')
        self.assertEqual(response.status_code, 404)

    def test_confirm_overwrite_opened_directly_goes_to_the_theme_selector(self):
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/themes/confirm_overwrite')
        self.assertRedirects(response, '/themes/select', fetch_redirect_response=False)

    def test_confirm_overwrite_rejects_a_bad_theme_name_without_logging_an_error(self):
        self.client.login(username=self.admin.username, password='password')
        with self.assertNoLogs(ERROR_LOGGER, level='ERROR'):
            response = self.client.post('/themes/confirm_overwrite', {'theme': '../etc'})
        self.assertTemplateUsed(response, 'error.html')
        self.assertContains(response, 'Invalid theme name', status_code=500)
