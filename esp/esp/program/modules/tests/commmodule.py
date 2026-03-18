from django.test import TestCase
from esp.program.modules.handlers.commmodule import _program_urls_in_text, CommModule
from unittest.mock import patch, MagicMock

class ProgramUrlsInTextTests(TestCase):
    
    def test_empty_text_returns_empty(self):
        self.assertEqual(_program_urls_in_text("", "Splash/2025_Spring"), [])
    
    def test_none_test_returns_empty(self):
        self.assertEqual(_program_urls_in_text(None, "Splash/2025_Spring"), [])
    
    def test_none_program_url_returns_empty(self):
        self.assertEqual(_program_urls_in_text("/learn/Splash/2024_Winter", None), [])

    def test_no_url_returns_empty(self):
        self.assertEqual(_program_urls_in_text("Hello World", "Splash/2025_Spring"), [])  
    
    def test_current_program_url_ignored(self):
        self.assertEqual(_program_urls_in_text("Visit /learn/Splash/2025_Spring to register", "Splash/2025_Spring"), [])  

    def test_different_program_url_found(self):
        text = 'See /learn/Splash/2024_Winter for past info'
        result = _program_urls_in_text(text, 'Splash/2025_Spring')
        self.assertIn('Splash/2024_Winter', result)
    
    def test_teach_url_found(self):
        text = 'Check /teach/HSSP/2023_Summer for teaching'
        result = _program_urls_in_text(text, 'Splash/2025_Spring')
        self.assertIn('HSSP/2023_Summer', result)

    def test_volunteer_url_found(self):
        text = 'See /volunteer/Spark/2024_Fall'
        result = _program_urls_in_text(text, 'Splash/2025_Spring')
        self.assertIn('Spark/2024_Fall', result)

    def test_multiple_urls_found(self):
        text = '/learn/Splash/2024_Winter and /teach/HSSP/2023_Summer'
        result = _program_urls_in_text(text, 'Splash/2025_Spring')
        self.assertIn('Splash/2024_Winter', result)
        self.assertIn('HSSP/2023_Summer', result)

    def test_duplicate_urls_deduplicated(self):
        text = '/learn/Splash/2024_Winter and /learn/Splash/2024_Winter again'
        result = _program_urls_in_text(text, 'Splash/2025_Spring')
        self.assertEqual(result.count('Splash/2024_Winter'), 1)

    def test_result_is_sorted(self):
        text = '/learn/Splash/2024_Winter /learn/HSSP/2023_Summer'
        result = _program_urls_in_text(text, 'Splash/2025_Spring')
        self.assertEqual(result, sorted(result))


class GetMailerWarningsTest(TestCase):

    def _make_filter_mock(self, useful_name=''):
        mock_filter = MagicMock()
        mock_filter.useful_name = useful_name
        return mock_filter

    def test_massive_mailer_warning(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_filter')):
            warnings = CommModule.get_mailer_warnings(2000, 1, 'SEND_TO_SELF')
            self.assertTrue(any('massive mailer' in w.lower() for w in warnings))

    def test_no_massive_mailer_warning_below_threshold(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_filter')):
            warnings = CommModule.get_mailer_warnings(1999, 1, 'SEND_TO_SELF')
            self.assertFalse(any('massive mailer' in w.lower() for w in warnings))

    def test_massive_mailer_warning_above_threshold(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_filter')):
            warnings = CommModule.get_mailer_warnings(2001, 1, 'SEND_TO_SELF')
            self.assertTrue(any('massive mailer' in w.lower() for w in warnings))

    def test_no_grade_filter_warning(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('all_students')):
            warnings = CommModule.get_mailer_warnings(100, 1, 'SEND_TO_SELF')
            self.assertTrue(any('grade' in w.lower() for w in warnings))

    def test_grade_filter_no_warning(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_range_filter')):
            warnings = CommModule.get_mailer_warnings(100, 1, 'SEND_TO_SELF')
            self.assertFalse(any('grade' in w.lower() for w in warnings))

    def test_invalid_listcount_handled(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_filter')):
            warnings = CommModule.get_mailer_warnings('invalid', 1, 'SEND_TO_SELF')
            self.assertIsInstance(warnings, list)

    def test_none_listcount_handled(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_filter')):
            warnings = CommModule.get_mailer_warnings(None, 1, 'SEND_TO_SELF')
            self.assertIsInstance(warnings, list)

    def test_no_warnings_for_small_list_with_grade_filter(self):
        with patch('esp.users.models.PersistentQueryFilter.getFilterFromID',
                   return_value=self._make_filter_mock('grade_filter')):
            warnings = CommModule.get_mailer_warnings(100, 1, 'SEND_TO_SELF')
            self.assertEqual(warnings, [])


class ApproxNumOfRecipientsTest(TestCase):

    def _make_filter_mock(self, user_count, users=None):
        mock_filter = MagicMock()
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = user_count
        mock_queryset.distinct.return_value = mock_queryset
        if users:
            mock_queryset.__getitem__ = lambda self, s: users[s]
        else:
            mock_queryset.__getitem__ = lambda self, s: []
        mock_filter.getList.return_value = mock_queryset
        return mock_filter

    def test_empty_list_returns_zero(self):
        mock_filter = self._make_filter_mock(0)
        sendto_fn = MagicMock(return_value=[])
        result = CommModule.approx_num_of_recipients(mock_filter, sendto_fn)
        self.assertEqual(result, 0)

    def test_single_user_single_email(self):
        mock_user = MagicMock()
        mock_filter = self._make_filter_mock(1, [mock_user])
        sendto_fn = MagicMock(return_value=['email@test.com'])
        result = CommModule.approx_num_of_recipients(mock_filter, sendto_fn)
        self.assertEqual(result, 1)

    def test_single_user_multiple_emails(self):
        mock_user = MagicMock()
        mock_filter = self._make_filter_mock(1, [mock_user])
        sendto_fn = MagicMock(return_value=['a@test.com', 'b@test.com'])
        result = CommModule.approx_num_of_recipients(mock_filter, sendto_fn)
        self.assertEqual(result, 2)

    def test_multiple_users_single_email_each(self):
        users = [MagicMock(), MagicMock(), MagicMock()]
        mock_filter = self._make_filter_mock(3, users)
        sendto_fn = MagicMock(return_value=['email@test.com'])
        result = CommModule.approx_num_of_recipients(mock_filter, sendto_fn)
        self.assertEqual(result, 3)

    def test_result_scales_with_emails_per_user(self):
        users = [MagicMock()]
        mock_filter = self._make_filter_mock(10, users)
        sendto_fn = MagicMock(return_value=['a@test.com', 'b@test.com', 'c@test.com'])
        result = CommModule.approx_num_of_recipients(mock_filter, sendto_fn)
        self.assertEqual(result, 30)