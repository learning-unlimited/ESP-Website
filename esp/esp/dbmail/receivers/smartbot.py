from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject, ClassSection
from esp.mailman import create_list, load_list_settings, add_list_member, set_list_moderator_password, apply_list_settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from esp.settings import USE_MAILMAN


class SmartBot(BaseHandler):

    def process(self, user, class_id, user_type):
        ## Don't get into an infinite loop
        if 'X-ESP-bot' in msg:
            self.send = False
            return

        msg['X-ESP-bot'] = "True"

        try:
            cls = ClassSubject.objects.get(id = class_id)
            sections = cls.sections.all()
        except ESPUser.DoesNotExist:
            return

        program = cls.parent_program
        self.recipients = ['%s Directors <%s>' % (program.niceName(), program.director_email)]

        user_type = user_type.strip().lower()

        if user_type in ('teachers','class'):
            self.recipients += ['%s %s <%s>' % (user.first_name,
                                                user.last_name,
                                                user.email)
                                for user in cls.teachers()     ]

        if user_type in ('students','class'):
            for section in sections:
                self.recipients += ['%s %s <%s>' % (user.first_name,
                                                    user.last_name,
                                                    user.email)
                                    for user in section.students()     ]

        if len(self.recipients) > 0:
            self.send = True

