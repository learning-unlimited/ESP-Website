from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import ClassSubject
from esp.mailman import create_list, load_list_settings, add_list_member, add_list_members, set_list_moderator_password, apply_list_settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site

class ClassList(BaseHandler):

    def process(self, user, class_id, user_type):
        if settings.USE_MAILMAN:
            self.process_mailman(user, class_id, user_type)
        else:
            self.process_nomailman(user, class_id, user_type)

    def process_nomailman(self, user, class_id, user_type):
        try:
            cls = ClassSubject.objects.get(id = class_id)
            sections = cls.sections.all()
        except ESPUser.DoesNotExist:
            return

        self.emailcode = cls.emailcode()

        program = cls.parent_program
        self.recipients = ['%s Directors <%s>' % (program.niceName(), program.director_email)]

        user_type = user_type.strip().lower()

        if user_type in ('teachers','class'):
            self.recipients += ['%s %s <%s>' % (user.first_name,
                                                user.last_name,
                                                user.email)
                                for user in cls.get_teachers()     ]

        if user_type in ('students','class'):
            for section in sections:
                self.recipients += ['%s %s <%s>' % (user.first_name,
                                                    user.last_name,
                                                    user.email)
                                    for user in section.students()     ]

        if len(self.recipients) > 0:
            self.send = True


    def process_mailman(self, user, class_id, user_type):
        if not (settings.USE_MAILMAN and 'mailman_moderator' in settings.DEFAULT_EMAIL_ADDRESSES.keys()):
            return
        try:
            cls = ClassSubject.objects.get(id = class_id)
            sections = cls.sections.all()
        except ESPUser.DoesNotExist:
            return

        # Create a class list in Mailman,
        # then bounce this email off to it

        list_name = "%s-%s" % (cls.emailcode(), user_type)

        create_list(list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])
        load_list_settings(list_name, "lists/class_mailman.config")

        if user_type != "teachers":
            for section in sections:
                add_list_members(list_name, section.students())

            apply_list_settings(list_name, {
                'moderator': [
                    settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'],
                    '%s-teachers@%s' % (cls.emailcode(),
                                        Site.objects.get_current().domain),
                    # In theory this is redundant, but it's included just in
                    # case.
                    cls.parent_program.director_email,
                ],
                'owner': [
                    settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'],
                    cls.parent_program.director_email,
                ],
                'subject_prefix': "[%s]" % (cls.parent_program.niceName(),),
            })
            send_mail("[ESP] Activated class mailing list: %s@%s" % (list_name, Site.objects.get_current().domain),
                      render_to_string("mailman/new_list_intro_teachers.txt",
                                       { 'classname': str(cls),
                                         'mod_password': set_list_moderator_password(list_name) }),
                      settings.DEFAULT_EMAIL_ADDRESSES['default'], ["%s-teachers@%s" % (cls.emailcode(), Site.objects.get_current().domain), ])
        else:
            apply_list_settings(list_name, {'default_member_moderation': False})
            apply_list_settings(list_name, {'generic_nonmember_action': 0})
            apply_list_settings(list_name, {'acceptable_aliases': "%s.*-(students|class)-.*@%s" % (cls.emailcode(), Site.objects.get_current().domain)})
            apply_list_settings(list_name, {'subject_prefix': "[%s]" % (cls.parent_program.niceName(),)})

        add_list_member(list_name, cls.parent_program.director_email)
        add_list_members(list_name, cls.get_teachers())
        if 'archive' in settings.DEFAULT_EMAIL_ADDRESSES:
            add_list_member(list_name, settings.DEFAULT_EMAIL_ADDRESSES['archive'])

        self.recipients = ["%s@%s" % (list_name, Site.objects.get_current().domain)]

        self.send = True


