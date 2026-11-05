"""Tests for esp.dbmail.sendto_fns and the MessageRequest sendto dispatch.

`sendto_fns` decides, for each recipient of a MessageRequest, which addresses
actually receive the mail: the user's own address, a guardian's, an emergency
contact's, or a combination. Every function there swallows exceptions and
returns `[]` on failure, so a regression cannot raise - it silently drops
recipients. These tests pin the address lists themselves rather than relying on
"no exception was raised".

The second half covers `MessageRequest.get_sendto_fn_callable()` and friends,
which resolve a `sendto_fn_name` field value to a callable in this module. That
resolution is the only thing tying the field choices to the implementations, so
it is tested against the real choice list.
"""

from __future__ import absolute_import

from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from esp.dbmail import sendto_fns
from esp.dbmail.models import MessageRequest
from esp.middleware.esperrormiddleware import ESPError_Log
from esp.program.models import RegistrationProfile
from esp.tests.factories import make_user
from esp.tests.util import CacheFlushTestCase
from esp.users.models import ContactInfo


def _make_contact(user, first_name, last_name, email):
    """Create a saved ContactInfo. `email` may be '' to model a blank address."""
    return ContactInfo.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
        e_mail=email,
    )


def _make_profile(user, guardian=None, emergency=None):
    """Give `user` a saved RegistrationProfile with the given contacts.

    No program is attached: RegistrationProfile.program is nullable, and
    getLastProfile() only orders by last_ts, so a program-less profile is the
    smallest fixture that the sendto functions will actually find.
    """
    return RegistrationProfile.objects.create(
        user=user,
        contact_guardian=guardian,
        contact_emergency=emergency,
        most_recent_profile=True,
    )


class _NoSuchAttributes(object):
    """Stand-in for a recipient that is not an ESPUser.

    The sendto functions are called on whatever the recipient query returns, and
    each one wraps its work in `except Exception`. Passing this object exercises
    that guard without mocking the code under test.
    """
    pass


class SendToSelfTest(CacheFlushTestCase):
    """send_to_self(): the user's own address, or nothing."""

    def test_returns_user_address_pair(self):
        user = make_user('Student', username='sendto_self_student')
        self.assertEqual(
            sendto_fns.send_to_self(user),
            [(user.email, user.name())],
        )

    def test_pair_is_email_then_name(self):
        user = make_user('Teacher', username='sendto_self_teacher')
        pairs = sendto_fns.send_to_self(user)
        self.assertEqual(len(pairs), 1)
        email, name = pairs[0]
        self.assertEqual(email, 'sendto_self_teacher@test.learningu.org')
        self.assertEqual(name, 'Teacher TestUser')

    def test_no_profile_needed(self):
        """send_to_self() reads the user row only, so it works with no profile."""
        user = make_user('Student', username='sendto_self_no_profile')
        self.assertFalse(
            RegistrationProfile.objects.filter(user=user).exists()
        )
        self.assertEqual(len(sendto_fns.send_to_self(user)), 1)

    def test_returns_empty_list_on_error(self):
        self.assertEqual(sendto_fns.send_to_self(_NoSuchAttributes()), [])


class SendToContactTest(CacheFlushTestCase):
    """send_to_guardian() / send_to_emergency(), built by _send_to_contact()."""

    def test_guardian_address_returned(self):
        user = make_user('Student', username='sendto_guardian_student')
        guardian = _make_contact(user, 'Gina', 'Guardian', 'gina@example.com')
        _make_profile(user, guardian=guardian)

        self.assertEqual(
            sendto_fns.send_to_guardian(user),
            [('gina@example.com', 'Gina Guardian')],
        )

    def test_emergency_address_returned(self):
        user = make_user('Student', username='sendto_emergency_student')
        emergency = _make_contact(user, 'Emmy', 'Emergency', 'emmy@example.com')
        _make_profile(user, emergency=emergency)

        self.assertEqual(
            sendto_fns.send_to_emergency(user),
            [('emmy@example.com', 'Emmy Emergency')],
        )

    def test_guardian_and_emergency_are_distinct_lookups(self):
        """send_to_emergency() must not fall back to the guardian contact."""
        user = make_user('Student', username='sendto_both_contacts_student')
        guardian = _make_contact(user, 'Gina', 'Guardian', 'gina2@example.com')
        emergency = _make_contact(user, 'Emmy', 'Emergency', 'emmy2@example.com')
        _make_profile(user, guardian=guardian, emergency=emergency)

        self.assertEqual(
            sendto_fns.send_to_guardian(user),
            [('gina2@example.com', 'Gina Guardian')],
        )
        self.assertEqual(
            sendto_fns.send_to_emergency(user),
            [('emmy2@example.com', 'Emmy Emergency')],
        )

    def test_missing_contact_returns_empty_list(self):
        """A profile with no guardian contact yields no addresses, not an error."""
        user = make_user('Student', username='sendto_no_guardian_student')
        _make_profile(user)

        self.assertEqual(sendto_fns.send_to_guardian(user), [])
        self.assertEqual(sendto_fns.send_to_emergency(user), [])

    def test_blank_contact_email_returns_empty_list(self):
        """A contact exists but has no address: nothing to send to."""
        user = make_user('Student', username='sendto_blank_email_student')
        guardian = _make_contact(user, 'Blank', 'Guardian', '')
        _make_profile(user, guardian=guardian)

        self.assertEqual(sendto_fns.send_to_guardian(user), [])

    def test_user_without_profile_returns_empty_list(self):
        """getLastProfile() returns an unsaved blank profile; its contacts are None."""
        user = make_user('Student', username='sendto_profileless_student')
        self.assertFalse(
            RegistrationProfile.objects.filter(user=user).exists()
        )

        self.assertEqual(sendto_fns.send_to_guardian(user), [])

    def test_returns_empty_list_on_error(self):
        self.assertEqual(sendto_fns.send_to_guardian(_NoSuchAttributes()), [])
        self.assertEqual(sendto_fns.send_to_emergency(_NoSuchAttributes()), [])

    def test_unknown_contact_kind_falls_back_to_guardian(self):
        """_send_to_contact() defaults to contact_guardian for unknown kinds.

        The getattr() default in _send_to_contact() means a typo'd contact name
        silently mails the guardian instead of raising. Only 'guardian' and
        'emergency' are built at module level today; this pins the fallback so
        the behaviour is a decision rather than an accident.
        """
        user = make_user('Student', username='sendto_unknown_kind_student')
        guardian = _make_contact(user, 'Gina', 'Guardian', 'gina3@example.com')
        _make_profile(user, guardian=guardian)

        send_to_typo = sendto_fns._send_to_contact('gaurdian')
        self.assertEqual(
            send_to_typo(user),
            [('gina3@example.com', 'Gina Guardian')],
        )

    def test_generated_function_metadata(self):
        """_send_to_contact() names and documents the function it builds."""
        self.assertEqual(sendto_fns.send_to_guardian.__name__, 'send_to_guardian')
        self.assertEqual(sendto_fns.send_to_emergency.__name__, 'send_to_emergency')
        self.assertIn('guardian', sendto_fns.send_to_guardian.__doc__)
        self.assertIn('emergency', sendto_fns.send_to_emergency.__doc__)


class SendToCombinationTest(CacheFlushTestCase):
    """_send_to_combination(): concatenation, in order, with duplicates dropped."""

    def setUp(self):
        super().setUp()
        self.user = make_user('Student', username='sendto_combo_student')
        self.guardian = _make_contact(
            self.user, 'Gina', 'Guardian', 'combo_gina@example.com')
        self.emergency = _make_contact(
            self.user, 'Emmy', 'Emergency', 'combo_emmy@example.com')
        _make_profile(self.user, guardian=self.guardian, emergency=self.emergency)

    def test_self_and_guardian(self):
        self.assertEqual(
            sendto_fns.send_to_self_and_guardian(self.user),
            [
                (self.user.email, self.user.name()),
                ('combo_gina@example.com', 'Gina Guardian'),
            ],
        )

    def test_self_and_emergency(self):
        self.assertEqual(
            sendto_fns.send_to_self_and_emergency(self.user),
            [
                (self.user.email, self.user.name()),
                ('combo_emmy@example.com', 'Emmy Emergency'),
            ],
        )

    def test_guardian_and_emergency_excludes_self(self):
        self.assertEqual(
            sendto_fns.send_to_guardian_and_emergency(self.user),
            [
                ('combo_gina@example.com', 'Gina Guardian'),
                ('combo_emmy@example.com', 'Emmy Emergency'),
            ],
        )

    def test_all_three_in_declaration_order(self):
        self.assertEqual(
            sendto_fns.send_to_self_and_guardian_and_emergency(self.user),
            [
                (self.user.email, self.user.name()),
                ('combo_gina@example.com', 'Gina Guardian'),
                ('combo_emmy@example.com', 'Emmy Emergency'),
            ],
        )

    def test_duplicate_email_kept_once_with_first_name(self):
        """Shared address between user and guardian is mailed once, not twice."""
        user = make_user('Student', username='sendto_dup_student')
        guardian = _make_contact(user, 'Gina', 'Guardian', user.email)
        _make_profile(user, guardian=guardian)

        self.assertEqual(
            sendto_fns.send_to_self_and_guardian(user),
            [(user.email, user.name())],
        )

    def test_missing_component_does_not_drop_the_others(self):
        user = make_user('Student', username='sendto_partial_student')
        _make_profile(user)

        self.assertEqual(
            sendto_fns.send_to_self_and_guardian_and_emergency(user),
            [(user.email, user.name())],
        )

    def test_failing_component_does_not_drop_the_others(self):
        """One raising sendto function must not discard the addresses of the rest."""
        def boom(user):
            raise ValueError('component failure')
        boom.__doc__ = 'Always raises.'

        combined = sendto_fns._send_to_combination([boom, sendto_fns.send_to_self])

        self.assertEqual(
            combined(self.user),
            [(self.user.email, self.user.name())],
        )

    def test_combination_of_nothing_is_empty(self):
        combined = sendto_fns._send_to_combination([])
        self.assertEqual(combined(self.user), [])

    def test_combination_names_and_docstrings(self):
        """Each combination is named for the admin dropdown and documents its parts."""
        for name in (
            'send_to_self_and_guardian',
            'send_to_self_and_emergency',
            'send_to_guardian_and_emergency',
            'send_to_self_and_guardian_and_emergency',
        ):
            fn = getattr(sendto_fns, name)
            self.assertEqual(fn.__name__, name)

        doc = sendto_fns.send_to_self_and_guardian_and_emergency.__doc__
        self.assertIn('send_to_self', doc)
        self.assertIn('send_to_guardian', doc)
        self.assertIn('send_to_emergency', doc)


class SendtoFnDispatchTest(CacheFlushTestCase):
    """MessageRequest resolution of a sendto_fn_name to a callable."""

    def test_every_field_choice_resolves_to_a_callable(self):
        """The field choices and this module must not drift apart."""
        for name, _label in MessageRequest.SENDTO_FN_CHOICES:
            fn = MessageRequest.get_sendto_fn_callable(name)
            self.assertTrue(callable(fn), '%r did not resolve to a callable' % name)

    def test_empty_name_means_send_to_self(self):
        """'' is the field default and the legacy 'mail the user only' behaviour."""
        self.assertIs(
            MessageRequest.get_sendto_fn_callable(MessageRequest.SEND_TO_SELF),
            sendto_fns.send_to_self,
        )

    def test_explicit_send_to_self_name_resolves(self):
        self.assertIs(
            MessageRequest.get_sendto_fn_callable(MessageRequest.SEND_TO_SELF_REAL),
            sendto_fns.send_to_self,
        )

    def test_named_choices_resolve_to_matching_functions(self):
        self.assertIs(
            MessageRequest.get_sendto_fn_callable(MessageRequest.SEND_TO_GUARDIAN),
            sendto_fns.send_to_guardian,
        )
        self.assertIs(
            MessageRequest.get_sendto_fn_callable(
                MessageRequest.SEND_TO_SELF_AND_GUARDIAN_AND_EMERGENCY),
            sendto_fns.send_to_self_and_guardian_and_emergency,
        )

    def test_is_sendto_fn_name_choice(self):
        self.assertTrue(
            MessageRequest.is_sendto_fn_name_choice(MessageRequest.SEND_TO_SELF))
        self.assertTrue(
            MessageRequest.is_sendto_fn_name_choice(MessageRequest.SEND_TO_SELF_REAL))
        self.assertTrue(
            MessageRequest.is_sendto_fn_name_choice(MessageRequest.SEND_TO_EMERGENCY))
        self.assertFalse(
            MessageRequest.is_sendto_fn_name_choice('send_to_nobody'))

    def test_unknown_name_raises_improperly_configured(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            MessageRequest.get_sendto_fn_callable('send_to_nobody')
        self.assertIn('not one of the available', str(ctx.exception))

    def test_choice_without_implementation_raises_improperly_configured(self):
        """A choice added to the field but never implemented here is caught."""
        choices = MessageRequest.SENDTO_FN_CHOICES + (('send_to_undefined', 'x'),)
        with patch.object(MessageRequest, 'SENDTO_FN_CHOICES', choices):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                MessageRequest.get_sendto_fn_callable('send_to_undefined')
        self.assertIn('does not define', str(ctx.exception))

    def test_non_callable_implementation_raises_improperly_configured(self):
        """A name that resolves to a non-callable attribute is caught too."""
        choices = MessageRequest.SENDTO_FN_CHOICES + (('send_to_not_callable', 'x'),)
        with patch.object(MessageRequest, 'SENDTO_FN_CHOICES', choices), \
                patch.object(sendto_fns, 'send_to_not_callable',
                             'not a function', create=True):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                MessageRequest.get_sendto_fn_callable('send_to_not_callable')
        self.assertIn('callable sendto function', str(ctx.exception))

    def test_get_sendto_fn_uses_the_instance_field(self):
        """get_sendto_fn() reads sendto_fn_name only, so an unsaved request works."""
        request = MessageRequest(
            sendto_fn_name=MessageRequest.SEND_TO_SELF_AND_GUARDIAN)
        self.assertIs(request.get_sendto_fn(), sendto_fns.send_to_self_and_guardian)

    def test_get_sendto_fn_defaults_to_send_to_self(self):
        request = MessageRequest()
        self.assertEqual(request.sendto_fn_name, MessageRequest.SEND_TO_SELF)
        self.assertIs(request.get_sendto_fn(), sendto_fns.send_to_self)

    def test_assert_is_valid_returns_the_callable(self):
        self.assertIs(
            MessageRequest.assert_is_valid_sendto_fn_or_ESPError(
                MessageRequest.SEND_TO_GUARDIAN),
            sendto_fns.send_to_guardian,
        )

    def test_assert_is_valid_accepts_the_empty_name(self):
        self.assertIs(
            MessageRequest.assert_is_valid_sendto_fn_or_ESPError(
                MessageRequest.SEND_TO_SELF),
            sendto_fns.send_to_self,
        )

    def test_assert_is_valid_raises_esperror_for_unknown_name(self):
        """Invalid names surface as ESPError, not ImproperlyConfigured."""
        with self.assertRaises(ESPError_Log):
            MessageRequest.assert_is_valid_sendto_fn_or_ESPError('send_to_nobody')

    def test_esperror_carries_the_explanation(self):
        """The raised ESPError must carry its message, not just its type.

        ESPError() takes (message, log). Passing the log flag positionally
        first means the message lands in `log` and is dropped, and the helper
        ends up raising the bare exception class - which the error middleware
        logs as an empty message and shows as a blank error page. These
        assertions pin the message so that mistake cannot come back.
        """
        with self.assertRaises(ESPError_Log) as ctx:
            MessageRequest.assert_is_valid_sendto_fn_or_ESPError('send_to_nobody')

        message = str(ctx.exception)
        self.assertIn('send_to_nobody', message)
        self.assertIn('Invalid sendto function', message)
        # The ImproperlyConfigured text is quoted into the explanation.
        self.assertIn('not one of the available', message)
        self.assertIn(
            settings.DEFAULT_EMAIL_ADDRESSES['support'], message)
