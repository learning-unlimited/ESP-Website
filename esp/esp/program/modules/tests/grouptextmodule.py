from unittest.mock import patch

from django.test import override_settings

from esp.program.models import RegistrationProfile
from esp.program.modules.handlers.grouptextmodule import GroupTextModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ContactInfo, ESPUser


class _UserFilter:
    def __init__(self, users):
        self.users = users

    def getList(self, model):
        return self.users


@override_settings(
    TWILIO_ACCOUNT_SID='test-account-sid',
    TWILIO_AUTH_TOKEN='test-auth-token',
    TWILIO_ACCOUNT_NUMBERS=['+12015550123'],
)
class GroupTextModuleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp(num_students=2)
        self.add_user_profiles()
        self.textable_user = self.students[0]
        self.missing_contact_user = self.students[1]

        profile = RegistrationProfile.objects.get(
            user=self.textable_user,
            program=self.program,
            most_recent_profile=True,
        )
        self.contact = ContactInfo.objects.create(
            user=self.textable_user,
            first_name=self.textable_user.first_name,
            last_name=self.textable_user.last_name,
            e_mail=self.textable_user.email,
            phone_cell='+12015550100',
            receive_txt_message=True,
        )
        profile.contact_user = self.contact
        profile.save()

    def _filter_for(self, *users):
        return _UserFilter(ESPUser.objects.filter(id__in=[u.id for u in users]).order_by('id'))

    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_send_messages_skips_users_without_contact_info(self, mock_client):
        log = GroupTextModule.sendMessages(
            self._filter_for(self.textable_user, self.missing_contact_user),
            'Hello from ESP',
        )

        self.assertIn('Could not find contact info for', log)
        mock_client.return_value.messages.create.assert_called_once_with(
            body='Hello from ESP',
            to='+12015550100',
            from_='+12015550123',
        )

    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_send_messages_respects_text_opt_out(self, mock_client):
        self.contact.receive_txt_message = False
        self.contact.save()

        log = GroupTextModule.sendMessages(
            self._filter_for(self.textable_user),
            'Hello from ESP',
        )

        self.assertIn('does not want text messages, fine', log)
        mock_client.return_value.messages.create.assert_not_called()

    @patch('esp.program.modules.handlers.grouptextmodule.Client')
    def test_send_messages_override_sends_to_opted_out_users(self, mock_client):
        self.contact.receive_txt_message = False
        self.contact.save()

        GroupTextModule.sendMessages(
            self._filter_for(self.textable_user),
            'Hello from ESP',
            override=True,
        )

        mock_client.return_value.messages.create.assert_called_once_with(
            body='Hello from ESP',
            to='+12015550100',
            from_='+12015550123',
        )
