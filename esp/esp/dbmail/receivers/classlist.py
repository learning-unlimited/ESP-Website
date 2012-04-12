from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject, ClassSection
from esp.mailman import create_list, load_list_settings, add_list_member, set_list_moderator_password, apply_list_settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

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


    def process_mailman(self, user, class_id, user_type):
        try:
            cls = ClassSubject.objects.get(id = class_id)
            sections = cls.sections.all()
        except ESPUser.DoesNotExist:
            return

        # Create a class list in Mailman,
        # then bounce this e-mail off to it

        list_name = "%s-%s" % (cls.emailcode(), user_type)

        create_list(list_name, "esp-moderators@mit.edu")
        load_list_settings(list_name, "lists/class_mailman.config")

        if user_type != "teachers":
            for section in sections:
                add_list_member(list_name, [x.email for x in section.students()])

            apply_list_settings(list_name, {'moderator': ['esp-moderators@mit.edu', '%s-teachers@esp.mit.edu' % cls.emailcode()]})
            send_mail("[ESP] Activated class mailing list: %s@esp.mit.edu" % list_name,
                      render_to_string("mailman/new_list_intro_teachers.txt", 
                                       { 'classname': str(cls),
                                         'mod_password': set_list_moderator_password(list_name) }), 
                      "esp@mit.edu", ["%s-teachers@esp.mit.edu" % cls.emailcode(), ])
        else:
            apply_list_settings(list_name, {'default_member_moderation': False})
            apply_list_settings(list_name, {'generic_nonmember_action': 0})
            apply_list_settings(list_name, {'acceptable_aliases': "%s.*-students-.*@esp.mit.edu" % (cls.emailcode(), )})

        add_list_member(list_name, [cls.parent_program.director_email])
        add_list_member(list_name, [x.email for x in cls.teachers()])

        self.recipients = ["%s@esp.mit.edu" % list_name]

        self.send = True

        
