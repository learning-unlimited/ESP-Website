from __future__ import absolute_import

from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from esp.dbmail.models import send_mail, AllowedSenderDomainValidator


class SendMailTest(TestCase):
    def test_cc(self):
        """ cc addresses get a Cc header and are actually delivered to,
        alongside the To and Bcc recipients. """
        mail.outbox = []
        send_mail('Subject', 'Body', settings.SERVER_EMAIL, ['to@example.com'],
                  bcc=['bcc@example.com'], cc=['cc@example.com'])
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.cc, ['cc@example.com'])
        self.assertEqual(set(message.recipients()),
                         {'to@example.com', 'cc@example.com', 'bcc@example.com'})
        self.assertIn('Cc: cc@example.com', message.message().as_string())
        self.assertNotIn('bcc@example.com', message.message().as_string())


class AllowedSenderDomainValidatorTest(TestCase):
    @override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'mit\.edu'])
    def test_uses_this_sites_domains(self):
        """ Validates against the current site's settings, not whatever they
        were when the model was defined. """
        validate = AllowedSenderDomainValidator()
        validate('splash@mit.edu')
        with self.assertRaises(ValidationError) as cm:
            validate('splash@esp-dev.mit.edu')
        self.assertEqual(cm.exception.messages, [r'Domain must match one of: mit\.edu'])
        with override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'mit\.edu', r'esp-dev\.mit\.edu']):
            validate('splash@esp-dev.mit.edu')
        for bad in ['splash@example.com', 'splash@mit.edu.example.com', '']:
            with self.assertRaises(ValidationError):
                validate(bad)

    def test_migration_state_is_the_same_on_every_site(self):
        """ The field deconstructs (and so appears in migrations) identically
        whatever the site's allowed domains, so `migrate` doesn't see
        unmigrated changes on sites whose domains differ from the generating
        one's. """
        from esp.program.models import Program
        field = Program._meta.get_field('director_email')
        with override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'mit\.edu']):
            one = field.deconstruct()
        with override_settings(ALLOWED_SENDER_EMAIL_DOMAINS=[r'esp\.mit\.edu', r'esp-dev\.mit\.edu']):
            other = field.deconstruct()
        self.assertEqual(one, other)
        self.assertEqual(one[3]['validators'], [AllowedSenderDomainValidator()])
