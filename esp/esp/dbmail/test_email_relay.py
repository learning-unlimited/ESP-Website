"""
Unit tests for email relay alias resolution and sender validation.

Tests import production helpers from esp.dbmail.relay (not local copies).
"""

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase

from esp.dbmail.models import PlainRedirect
from esp.dbmail.relay import (
    FORWARDER_HEADER,
    get_final_recipients,
    get_final_sender,
    has_been_forwarded,
    resolve_aliases_via_espuser,
    resolve_aliases_via_plain_redirect,
    select_sender_by_priority,
    split_recipients,
    users_for_from_field,
)
from esp.users.models import ESPUser


class PlainRedirectLookupTest(TestCase):
    """Tests for PlainRedirect-based alias resolution."""

    def setUp(self):
        PlainRedirect.objects.create(original='directors', destination='alice@example.com')
        PlainRedirect.objects.create(original='splash', destination='bob@example.com,carol@example.com')
        PlainRedirect.objects.create(original='SPLASH2', destination='dave@example.com')
        PlainRedirect.objects.create(original='empty', destination='')
        PlainRedirect.objects.create(
            original='internal',
            destination='someone@mit.learningu.org',
        )

    def test_basic_lookup_resolves_address(self):
        result = resolve_aliases_via_plain_redirect(['directors@mit.learningu.org'])
        self.assertIn('alice@example.com', result)

    def test_comma_separated_destinations_are_expanded(self):
        result = resolve_aliases_via_plain_redirect(['splash@mit.learningu.org'])
        self.assertIn('bob@example.com', result)
        self.assertIn('carol@example.com', result)
        self.assertEqual(len(result), 2)

    def test_lookup_is_case_insensitive(self):
        result = resolve_aliases_via_plain_redirect(['SPLASH2@mit.learningu.org'])
        self.assertIn('dave@example.com', result)

    def test_empty_destination_is_excluded(self):
        result = resolve_aliases_via_plain_redirect(['empty@mit.learningu.org'])
        self.assertEqual(result, [])

    def test_nonexistent_alias_returns_empty_list(self):
        result = resolve_aliases_via_plain_redirect(['doesnotexist@mit.learningu.org'])
        self.assertEqual(result, [])

    def test_internal_learningu_destination_is_filtered_out(self):
        result = resolve_aliases_via_plain_redirect(['internal@mit.learningu.org'])
        self.assertEqual(result, [])

    def test_empty_alias_list_returns_empty(self):
        self.assertEqual(resolve_aliases_via_plain_redirect([]), [])

    def test_multiple_aliases_resolved_together(self):
        result = resolve_aliases_via_plain_redirect([
            'directors@mit.learningu.org',
            'splash@mit.learningu.org',
        ])
        self.assertIn('alice@example.com', result)
        self.assertIn('bob@example.com', result)
        self.assertIn('carol@example.com', result)


class ESPUserAliasResolutionTest(TestCase):
    """Tests for ESPUser-based alias resolution via username."""

    def setUp(self):
        self.user1 = ESPUser.objects.create_user(
            username='jsmith', email='jsmith@gmail.com', password='pw'
        )
        self.user2 = ESPUser.objects.create_user(
            username='JDOE', email='jdoe@hotmail.com', password='pw'
        )
        self.internal_user = ESPUser.objects.create_user(
            username='internal_teacher',
            email='internal_teacher@mit.learningu.org',
            password='pw',
        )

    def test_alias_resolves_to_user_email(self):
        result = resolve_aliases_via_espuser(['jsmith@mit.learningu.org'])
        self.assertIn('jsmith@gmail.com', result)

    def test_alias_resolution_is_case_insensitive(self):
        result = resolve_aliases_via_espuser(['jdoe@mit.learningu.org'])
        self.assertIn('jdoe@hotmail.com', result)

    def test_users_with_internal_email_are_filtered_out(self):
        result = resolve_aliases_via_espuser(['internal_teacher@mit.learningu.org'])
        self.assertEqual(result, [])

    def test_unknown_alias_returns_empty_list(self):
        self.assertEqual(resolve_aliases_via_espuser(['nobody@mit.learningu.org']), [])

    def test_empty_alias_list_returns_empty(self):
        self.assertEqual(resolve_aliases_via_espuser([]), [])

    def test_multiple_aliases_resolved_together(self):
        result = resolve_aliases_via_espuser([
            'jsmith@mit.learningu.org',
            'jdoe@mit.learningu.org',
        ])
        self.assertIn('jsmith@gmail.com', result)
        self.assertIn('jdoe@hotmail.com', result)


class RecipientSplittingTest(TestCase):
    """Tests for filtering recipients into external, alias, and invalid buckets."""

    def test_external_address_goes_to_external_list(self):
        external, aliases, invalid = split_recipients(['alice@example.com'])
        self.assertEqual(external, ['alice@example.com'])
        self.assertEqual(aliases, [])
        self.assertEqual(invalid, [])

    def test_learningu_org_address_goes_to_aliases(self):
        external, aliases, invalid = split_recipients(['alice@mit.learningu.org'])
        self.assertEqual(aliases, ['alice@mit.learningu.org'])
        self.assertEqual(external, [])
        self.assertEqual(invalid, [])

    def test_address_without_at_sign_goes_to_invalid(self):
        external, aliases, invalid = split_recipients(['notanemail'])
        self.assertEqual(invalid, ['notanemail'])
        self.assertEqual(external, [])
        self.assertEqual(aliases, [])

    def test_mixed_recipient_list_is_split_correctly(self):
        external, aliases, invalid = split_recipients([
            'real@example.com',
            'alias@school.learningu.org',
            'badaddress',
        ])
        self.assertEqual(external, ['real@example.com'])
        self.assertEqual(aliases, ['alias@school.learningu.org'])
        self.assertEqual(invalid, ['badaddress'])

    def test_empty_recipient_list(self):
        external, aliases, invalid = split_recipients([])
        self.assertEqual(external, [])
        self.assertEqual(aliases, [])
        self.assertEqual(invalid, [])


class SenderValidationTest(TestCase):
    """Tests for sender lookup: external email vs. internal username."""

    def setUp(self):
        self.user = ESPUser.objects.create_user(
            username='sender1', email='sender@external.com', password='pw'
        )

    def test_external_sender_found_by_email(self):
        users = users_for_from_field('sender@external.com')
        self.assertEqual(list(users), [self.user])

    def test_external_sender_lookup_is_case_insensitive(self):
        users = users_for_from_field('SENDER@EXTERNAL.COM')
        self.assertEqual(list(users), [self.user])

    def test_internal_sender_found_by_username(self):
        from_field = 'sender1@%s' % settings.EMAIL_HOST_SENDER
        users = users_for_from_field(from_field)
        self.assertEqual(list(users), [self.user])

    def test_sender_with_display_name_is_parsed(self):
        users = users_for_from_field('Alice Smith <sender@external.com>')
        self.assertEqual(list(users), [self.user])

    def test_unknown_sender_returns_empty_queryset(self):
        self.assertFalse(users_for_from_field('nobody@unknown.com').exists())

    def test_empty_from_field_returns_empty_queryset(self):
        self.assertFalse(users_for_from_field('').exists())

    def test_none_from_field_returns_empty_queryset(self):
        self.assertFalse(users_for_from_field(None).exists())

    def test_whitespace_only_from_field_returns_empty_queryset(self):
        self.assertFalse(users_for_from_field('   ').exists())


class SenderPriorityTest(TestCase):
    """Priority: Administrator > Teacher > Volunteer > Student > Educator."""

    def _make_user(self, username, email, group_name=None):
        u = ESPUser.objects.create_user(username=username, email=email, password='pw')
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            u.groups.add(group)
        return u

    def test_single_user_is_returned_directly(self):
        user = self._make_user('solo', 'solo@x.com')
        self.assertEqual(select_sender_by_priority([user]), user)

    def test_administrator_beats_teacher(self):
        teacher = self._make_user('teacher1', 'shared@x.com', 'Teacher')
        admin = self._make_user('admin1', 'shared@x.com', 'Administrator')
        self.assertEqual(select_sender_by_priority([teacher, admin]), admin)

    def test_teacher_beats_student(self):
        student = self._make_user('student1', 'shared@x.com', 'Student')
        teacher = self._make_user('teacher1', 'shared@x.com', 'Teacher')
        self.assertEqual(select_sender_by_priority([student, teacher]), teacher)

    def test_volunteer_beats_student(self):
        student = self._make_user('student1', 'shared@x.com', 'Student')
        volunteer = self._make_user('volunteer1', 'shared@x.com', 'Volunteer')
        self.assertEqual(select_sender_by_priority([student, volunteer]), volunteer)

    def test_student_beats_educator(self):
        educator = self._make_user('edu1', 'shared@x.com', 'Educator')
        student = self._make_user('student1', 'shared@x.com', 'Student')
        self.assertEqual(select_sender_by_priority([educator, student]), student)

    def test_no_group_match_falls_back_to_first_user(self):
        u1 = self._make_user('first', 'shared@x.com')
        u2 = self._make_user('second', 'shared@x.com')
        self.assertEqual(select_sender_by_priority([u1, u2]), u1)

    def test_empty_user_list_returns_none(self):
        self.assertIsNone(select_sender_by_priority([]))

    def test_full_hierarchy_ordering(self):
        educator = self._make_user('edu', 'h@x.com', 'Educator')
        student = self._make_user('stu', 'h@x.com', 'Student')
        volunteer = self._make_user('vol', 'h@x.com', 'Volunteer')
        teacher = self._make_user('tea', 'h@x.com', 'Teacher')
        admin = self._make_user('adm', 'h@x.com', 'Administrator')
        all_users = [educator, student, volunteer, teacher, admin]
        self.assertEqual(select_sender_by_priority(all_users), admin)
        self.assertEqual(
            select_sender_by_priority([educator, student, volunteer, teacher]),
            teacher,
        )
        self.assertEqual(
            select_sender_by_priority([educator, student, volunteer]),
            volunteer,
        )
        self.assertEqual(select_sender_by_priority([educator, student]), student)
        self.assertEqual(select_sender_by_priority([educator]), educator)

    def test_get_final_sender_uses_priority(self):
        self._make_user('teacher1', 'shared@x.com', 'Teacher')
        admin = self._make_user('admin1', 'shared@x.com', 'Administrator')
        self.assertEqual(get_final_sender('shared@x.com'), admin)


class EndToEndRelayLogicTest(TestCase):
    """Integration-style tests for get_final_recipients pipeline."""

    def setUp(self):
        PlainRedirect.objects.create(original='directors', destination='dir@example.com')
        self.user = ESPUser.objects.create_user(
            username='teacher1', email='teacher@gmail.com', password='pw'
        )

    def test_mix_of_external_and_alias_recipients(self):
        final = get_final_recipients([
            'real@example.com',
            'directors@mit.learningu.org',
        ])
        self.assertIn('real@example.com', final)
        self.assertIn('dir@example.com', final)

    def test_alias_resolved_via_espuser_username(self):
        final = get_final_recipients(['teacher1@mit.learningu.org'])
        self.assertIn('teacher@gmail.com', final)

    def test_all_learningu_aliases_with_no_matches_gives_empty(self):
        final = get_final_recipients(['unknown@mit.learningu.org'])
        self.assertEqual(final, [])

    def test_purely_external_recipients_pass_through_unchanged(self):
        final = get_final_recipients(['alice@example.com', 'bob@example.com'])
        self.assertEqual(final, ['alice@example.com', 'bob@example.com'])

    def test_duplicates_are_removed_preserving_order(self):
        PlainRedirect.objects.create(original='dup', destination='real@example.com')
        final = get_final_recipients([
            'real@example.com',
            'dup@mit.learningu.org',
        ])
        self.assertEqual(final, ['real@example.com'])


class ForwardedHeaderTest(TestCase):
    def test_detects_forwarder_header_in_bytes(self):
        raw = b'From: a@b.com\n' + FORWARDER_HEADER.encode('utf-8') + b'\n\nbody'
        self.assertTrue(has_been_forwarded(raw))

    def test_detects_forwarder_header_in_str(self):
        raw = 'From: a@b.com\n%s\n\nbody' % FORWARDER_HEADER
        self.assertTrue(has_been_forwarded(raw))

    def test_missing_header_is_false(self):
        self.assertFalse(has_been_forwarded(b'From: a@b.com\n\nhello'))
        self.assertFalse(has_been_forwarded(''))
        self.assertFalse(has_been_forwarded(None))
