from __future__ import absolute_import
from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import ClassSubject
from esp.mailman import create_list, add_list_members, set_list_moderator_password, apply_list_settings
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
        self.recipients = [ESPUser.email_sendto_address(program.director_email, '%s Directors' % (program.niceName()))]

        user_type = user_type.strip().lower()

        if user_type in ('teachers', 'class'):
            self.recipients += [user.get_email_sendto_address()
                                for user in cls.get_teachers()     ]

        if user_type in ('students', 'class'):
            for section in sections:
                self.recipients += [user.get_email_sendto_address()
                                    for user in section.students()     ]

        if len(self.recipients) > 0:
            self.send = True


    def process_mailman(self, user, class_id, user_type):
        if not (settings.USE_MAILMAN and 'mailman_moderator' in list(settings.DEFAULT_EMAIL_ADDRESSES.keys())):
            return
        try:
            cls = ClassSubject.objects.get(id = class_id)
            sections = cls.sections.all()
        except ESPUser.DoesNotExist:
            return

        # Create a class list in Mailman,
        # then bounce this email off to it

        list_name = "%s-%s" % (cls.emailcode(), user_type)

        # Without the list, nothing below can work, and the email would go to
        # a list address that doesn't exist: let a failure stop here. The
        # mailgate logs it and bounces the email, and the next email to the
        # list tries the setup again.
        created = create_list(list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])
        # It can already exist when two first emails to it arrive at once, or
        # after an earlier setup failed partway (that failure was logged).
        # The setup below is then redone, except for a new moderator password
        # and its notice: the password in the first notice must keep working.

        if user_type != "teachers":
            apply_list_settings(list_name, listfile='lists/class_mailman.config', data={
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
            }, errors='log')
            if created:
                send_mail("[ESP] Activated class mailing list: %s@%s" % (list_name, Site.objects.get_current().domain),
                          render_to_string("mailman/new_list_intro_teachers.txt",
                                           { 'classname': str(cls),
                                             'mod_password': set_list_moderator_password(list_name, errors='log') }),
                          settings.DEFAULT_EMAIL_ADDRESSES['default'], ["%s-teachers@%s" % (cls.emailcode(), Site.objects.get_current().domain), ])
        else:
            # A new Mailman list holds non-member posts until this runs. Posts
            # can arrive in that window, e.g. the activation notice and
            # moderation requests from the students list when someone emails
            # both lists at once. They are released once the members are
            # added, below.
            apply_list_settings(list_name, listfile='lists/class_mailman.config', data={
                'generic_nonmember_action': 0,
                'default_member_moderation': False,
                'acceptable_aliases': "%s.*-(students|class)-.*@%s" % (cls.emailcode(), Site.objects.get_current().domain),
                'subject_prefix': "[%s]" % (cls.parent_program.niceName(),),
            }, errors='log')

        # All the members in one add_members run.
        members = [cls.parent_program.director_email] + list(cls.get_teachers())
        if 'archive' in settings.DEFAULT_EMAIL_ADDRESSES:
            members.append(settings.DEFAULT_EMAIL_ADDRESSES['archive'])
        if user_type != "teachers":
            for section in sections:
                members += list(section.students())
        add_list_members(list_name, members, errors='log')

        if user_type == "teachers":
            # Release posts held only for being from a non-member, as if the
            # setting above had been there all along. This must come after
            # the members are added: an approved post goes out at once to the
            # list's members as they are then, so releasing it earlier
            # delivers it to nobody.
            apply_list_settings(list_name, {}, release_nonmember_holds=True, errors='log')

        self.recipients = ["%s@%s" % (list_name, Site.objects.get_current().domain)]

        self.send = True

