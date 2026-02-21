"""
Unit tests for email relay logic (PR #3832 / Issue #3977).

Covers:
- learningu.org alias filtering from recipient lists
- PlainRedirect lookups (case-insensitive, null-exclusion, comma-split)
- ESPUser alias resolution via username lookup
- Sender validation (sender must have a registered account)
- Sender lookup for internal (EMAIL_HOST_SENDER) vs. external addresses
- User priority hierarchy when multiple accounts share an email
- Edge cases: empty recipients, malformed addresses, no account
"""

from __future__ import absolute_import

import itertools

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.functions import Lower
from django.test import TestCase

from esp.dbmail.models import PlainRedirect
from esp.users.models import ESPUser

# The learningu.org alias domain used by the relay (from PR #3832)
LEARNINGU_DOMAIN = '.learningu.org'


# ---------------------------------------------------------------------------
# Helpers that mirror the relay logic in mailgate.py (PR #3832)
# These live here so tests remain pure unit tests without importing the script.
# ---------------------------------------------------------------------------

def split_recipients(raw_recipients):
    """
    Partition a list of raw recipient strings into:
      - external_addrs: real, non-learningu.org addresses
      - aliases:        learningu.org addresses to be resolved
      - invalid:        strings with no '@' sign
    """
    external_addrs = []
    aliases = []
    invalid = []
    for addr in raw_recipients:
        if addr.endswith(LEARNINGU_DOMAIN):
            aliases.append(addr)
        elif '@' in addr:
            external_addrs.append(addr)
        else:
            invalid.append(addr)
    return external_addrs, aliases, invalid


def resolve_aliases_via_plain_redirect(aliases):
    """
    Look up PlainRedirect rows whose `original` matches the local part of
    each alias.  Comma-separated destinations are expanded, and any
    destination that itself ends in LEARNINGU_DOMAIN is filtered out.
    Returns a flat list of resolved email addresses.
    """
    local_parts = [a.split('@')[0].lower() for a in aliases]
    redirects = (
        PlainRedirect.objects
        .annotate(original_lower=Lower('original'))
        .filter(original_lower__in=local_parts)
        .exclude(destination__isnull=True)
        .exclude(destination='')
    )
    expanded = list(itertools.chain.from_iterable(
        r.destination.split(',') for r in redirects
    ))
    return [addr for addr in expanded if not addr.endswith(LEARNINGU_DOMAIN)]


def resolve_aliases_via_espuser(aliases):
    """
    Look up ESPUser rows whose username matches the local part of each alias.
    Returns a list of the users' email addresses, excluding any that end in
    LEARNINGU_DOMAIN.
    """
    local_parts = [a.split('@')[0].lower() for a in aliases]
    users = (
        ESPUser.objects
        .annotate(username_lower=Lower('username'))
        .filter(username_lower__in=local_parts)
    )
    return [u.email for u in users if not u.email.endswith(LEARNINGU_DOMAIN)]


def validate_sender_and_get_users(from_field):
    """
    Given the raw `from_field` string (e.g. 'Name <user@host>'), extract the
    email address and return a queryset of matching ESPUser objects.
    Returns an empty queryset when the address is blank or None.
    """
    if not from_field or not from_field.strip():
        return ESPUser.objects.none()

    addr = from_field.strip()
    if '<' in addr and '>' in addr:
        addr = addr.split('<')[1].split('>')[0]

    if addr.endswith(settings.EMAIL_HOST_SENDER):
        return ESPUser.objects.filter(
            username__iexact=addr.split('@')[0]
        ).order_by('date_joined')
    else:
        return ESPUser.objects.filter(
            email__iexact=addr
        ).order_by('date_joined')


def select_sender_by_priority(users):
    """
    Given a queryset/list of ESPUser objects, return the single user to use
    as the email sender, using the priority hierarchy:
      Administrator > Teacher > Volunteer > Student > Educator
    Falls back to the first (earliest date_joined) user when no group matches.
    """
    users = list(users)
    if not users:
        return None
    if len(users) == 1:
        return users[0]

    for group_name in ['Administrator', 'Teacher', 'Volunteer', 'Student', 'Educator']:
        group_users = [u for u in users if u.groups.filter(name=group_name).exists()]
        if group_users:
            return group_users[0]

    return users[0]


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class PlainRedirectLookupTest(TestCase):
    """Tests for PlainRedirect-based alias resolution."""

    def setUp(self):
        PlainRedirect.objects.create(original='directors', destination='alice@example.com')
        PlainRedirect.objects.create(original='splash',    destination='bob@example.com,carol@example.com')
        PlainRedirect.objects.create(original='SPLASH2',   destination='dave@example.com')
        PlainRedirect.objects.create(original='empty',     destination='')
        PlainRedirect.objects.create(
            original='internal',
            destination='someone@mit.learningu.org'
        )

    def test_basic_lookup_resolves_address(self):
        aliases = ['directors@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
        self.assertIn('alice@example.com', result)

    def test_comma_separated_destinations_are_expanded(self):
        aliases = ['splash@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
        self.assertIn('bob@example.com', result)
        self.assertIn('carol@example.com', result)
        self.assertEqual(len(result), 2)

    def test_lookup_is_case_insensitive(self):
        aliases = ['SPLASH2@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
        self.assertIn('dave@example.com', result)

    def test_empty_destination_is_excluded(self):
        aliases = ['empty@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
        self.assertEqual(result, [])

    def test_nonexistent_alias_returns_empty_list(self):
        aliases = ['doesnotexist@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
        self.assertEqual(result, [])

    def test_internal_learningu_destination_is_filtered_out(self):
        aliases = ['internal@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
        self.assertEqual(result, [],
            "Resolved addresses ending in learningu.org should be filtered out")

    def test_empty_alias_list_returns_empty(self):
        result = resolve_aliases_via_plain_redirect([])
        self.assertEqual(result, [])

    def test_multiple_aliases_resolved_together(self):
        aliases = ['directors@mit.learningu.org', 'splash@mit.learningu.org']
        result = resolve_aliases_via_plain_redirect(aliases)
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
            password='pw'
        )

    def test_alias_resolves_to_user_email(self):
        aliases = ['jsmith@mit.learningu.org']
        result = resolve_aliases_via_espuser(aliases)
        self.assertIn('jsmith@gmail.com', result)

    def test_alias_resolution_is_case_insensitive(self):
        aliases = ['jdoe@mit.learningu.org']
        result = resolve_aliases_via_espuser(aliases)
        self.assertIn('jdoe@hotmail.com', result)

    def test_users_with_internal_email_are_filtered_out(self):
        aliases = ['internal_teacher@mit.learningu.org']
        result = resolve_aliases_via_espuser(aliases)
        self.assertEqual(result, [],
            "Users whose own email ends in learningu.org must be filtered out")

    def test_unknown_alias_returns_empty_list(self):
        aliases = ['nobody@mit.learningu.org']
        result = resolve_aliases_via_espuser(aliases)
        self.assertEqual(result, [])

    def test_empty_alias_list_returns_empty(self):
        result = resolve_aliases_via_espuser([])
        self.assertEqual(result, [])

    def test_multiple_aliases_resolved_together(self):
        aliases = ['jsmith@mit.learningu.org', 'jdoe@mit.learningu.org']
        result = resolve_aliases_via_espuser(aliases)
        self.assertIn('jsmith@gmail.com', result)
        self.assertIn('jdoe@hotmail.com', result)


class RecipientSplittingTest(TestCase):
    """Tests for filtering recipients into external, alias, and invalid buckets."""

    def test_external_address_goes_to_external_list(self):
        external, aliases, invalid = split_recipients(['alice@example.com'])
        self.assertIn('alice@example.com', external)
        self.assertEqual(aliases, [])
        self.assertEqual(invalid, [])

    def test_learningu_org_address_goes_to_aliases(self):
        external, aliases, invalid = split_recipients(['alice@mit.learningu.org'])
        self.assertIn('alice@mit.learningu.org', aliases)
        self.assertEqual(external, [])
        self.assertEqual(invalid, [])

    def test_address_without_at_sign_goes_to_invalid(self):
        external, aliases, invalid = split_recipients(['notanemail'])
        self.assertIn('notanemail', invalid)
        self.assertEqual(external, [])
        self.assertEqual(aliases, [])

    def test_mixed_recipient_list_is_split_correctly(self):
        recipients = [
            'real@example.com',
            'alias@school.learningu.org',
            'badaddress',
        ]
        external, aliases, invalid = split_recipients(recipients)
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
        users = validate_sender_and_get_users('sender@external.com')
        self.assertEqual(list(users), [self.user])

    def test_external_sender_lookup_is_case_insensitive(self):
        users = validate_sender_and_get_users('SENDER@EXTERNAL.COM')
        self.assertEqual(list(users), [self.user])

    def test_internal_sender_found_by_username(self):
        from_field = 'sender1@%s' % settings.EMAIL_HOST_SENDER
        users = validate_sender_and_get_users(from_field)
        self.assertEqual(list(users), [self.user])

    def test_sender_with_display_name_is_parsed(self):
        from_field = 'Alice Smith <sender@external.com>'
        users = validate_sender_and_get_users(from_field)
        self.assertEqual(list(users), [self.user])

    def test_unknown_sender_returns_empty_queryset(self):
        users = validate_sender_and_get_users('nobody@unknown.com')
        self.assertFalse(users.exists())

    def test_empty_from_field_returns_empty_queryset(self):
        users = validate_sender_and_get_users('')
        self.assertFalse(users.exists())

    def test_none_from_field_returns_empty_queryset(self):
        users = validate_sender_and_get_users(None)
        self.assertFalse(users.exists())

    def test_whitespace_only_from_field_returns_empty_queryset(self):
        users = validate_sender_and_get_users('   ')
        self.assertFalse(users.exists())


class SenderPriorityTest(TestCase):
    """
    Tests for the user priority hierarchy used when multiple accounts share
    the same email address:
      Administrator > Teacher > Volunteer > Student > Educator
    """

    def _make_user(self, username, email, group_name=None):
        u = ESPUser.objects.create_user(username=username, email=email, password='pw')
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            u.groups.add(group)
        return u

    def test_single_user_is_returned_directly(self):
        user = self._make_user('solo', 'solo@x.com')
        selected = select_sender_by_priority([user])
        self.assertEqual(selected, user)

    def test_administrator_beats_teacher(self):
        teacher = self._make_user('teacher1', 'shared@x.com', 'Teacher')
        admin   = self._make_user('admin1',   'shared@x.com', 'Administrator')
        selected = select_sender_by_priority([teacher, admin])
        self.assertEqual(selected, admin)

    def test_teacher_beats_student(self):
        student = self._make_user('student1', 'shared@x.com', 'Student')
        teacher = self._make_user('teacher1', 'shared@x.com', 'Teacher')
        selected = select_sender_by_priority([student, teacher])
        self.assertEqual(selected, teacher)

    def test_volunteer_beats_student(self):
        student   = self._make_user('student1',   'shared@x.com', 'Student')
        volunteer = self._make_user('volunteer1', 'shared@x.com', 'Volunteer')
        selected = select_sender_by_priority([student, volunteer])
        self.assertEqual(selected, volunteer)

    def test_student_beats_educator(self):
        educator = self._make_user('edu1',      'shared@x.com', 'Educator')
        student  = self._make_user('student1',  'shared@x.com', 'Student')
        selected = select_sender_by_priority([educator, student])
        self.assertEqual(selected, student)

    def test_no_group_match_falls_back_to_first_user(self):
        u1 = self._make_user('first',  'shared@x.com')
        u2 = self._make_user('second', 'shared@x.com')
        selected = select_sender_by_priority([u1, u2])
        self.assertEqual(selected, u1)

    def test_empty_user_list_returns_none(self):
        selected = select_sender_by_priority([])
        self.assertIsNone(selected)

    def test_full_hierarchy_ordering(self):
        educator  = self._make_user('edu',  'h@x.com', 'Educator')
        student   = self._make_user('stu',  'h@x.com', 'Student')
        volunteer = self._make_user('vol',  'h@x.com', 'Volunteer')
        teacher   = self._make_user('tea',  'h@x.com', 'Teacher')
        admin     = self._make_user('adm',  'h@x.com', 'Administrator')
        all_users = [educator, student, volunteer, teacher, admin]

        self.assertEqual(select_sender_by_priority(all_users), admin)
        self.assertEqual(select_sender_by_priority([educator, student, volunteer, teacher]), teacher)
        self.assertEqual(select_sender_by_priority([educator, student, volunteer]), volunteer)
        self.assertEqual(select_sender_by_priority([educator, student]), student)
        self.assertEqual(select_sender_by_priority([educator]), educator)


class EndToEndRelayLogicTest(TestCase):
    """
    Integration-style tests that exercise the full alias-resolution pipeline
    (split → PlainRedirect resolve → ESPUser resolve → merge).
    """

    def setUp(self):
        PlainRedirect.objects.create(original='directors', destination='dir@example.com')
        self.user = ESPUser.objects.create_user(
            username='teacher1', email='teacher@gmail.com', password='pw'
        )

    def test_mix_of_external_and_alias_recipients(self):
        raw = ['real@example.com', 'directors@mit.learningu.org']
        external, aliases, _ = split_recipients(raw)
        resolved = resolve_aliases_via_plain_redirect(aliases)
        resolved += resolve_aliases_via_espuser(aliases)
        final = external + resolved
        self.assertIn('real@example.com', final)
        self.assertIn('dir@example.com', final)

    def test_alias_resolved_via_espuser_username(self):
        raw = ['teacher1@mit.learningu.org']
        external, aliases, _ = split_recipients(raw)
        resolved = resolve_aliases_via_espuser(aliases)
        self.assertIn('teacher@gmail.com', resolved)

    def test_all_learningu_aliases_with_no_matches_gives_empty(self):
        raw = ['unknown@mit.learningu.org']
        external, aliases, _ = split_recipients(raw)
        plain_resolved = resolve_aliases_via_plain_redirect(aliases)
        user_resolved  = resolve_aliases_via_espuser(aliases)
        final = external + plain_resolved + user_resolved
        self.assertEqual(final, [],
            "Email with no resolvable aliases and no real recipients should produce empty list")

    def test_purely_external_recipients_pass_through_unchanged(self):
        raw = ['alice@example.com', 'bob@example.com']
        external, aliases, _ = split_recipients(raw)
        resolved = resolve_aliases_via_plain_redirect(aliases) + resolve_aliases_via_espuser(aliases)
        final = external + resolved
        self.assertCountEqual(final, ['alice@example.com', 'bob@example.com'])
