from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject, ClassSection
from esp.mailman import create_list, load_list_settings, add_list_member, set_list_moderator_password, apply_list_settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site
DEBUG=True
DEBUG=False

class SectionList(BaseHandler):

    def process(self, user, class_id, section_num, user_type):
        if settings.USE_MAILMAN:
            self.process_mailman(user, class_id, section_num, user_type)
        else:
            self.process_nomailman(user, class_id, section_num, user_type)

    def process_nomailman(self, user, class_id, section_num, user_type):
        try:
            cls = ClassSubject.objects.get(id=int(class_id))
            section = filter(lambda s: s.index() == int(section_num), cls.sections.all())[0]
        except:
            return

        program = cls.parent_program
        self.recipients = ['%s Directors <%s>' % (program.niceName(), program.director_email)]

        user_type = user_type.strip().lower()

        if user_type in ('teachers','class'):
            self.recipients += ['%s %s <%s>' % (user.first_name,
                                                user.last_name,
                                                user.email)
                                for user in section.parent_class.teachers()     ]

        if user_type in ('students','class'):
            self.recipients += ['%s %s <%s>' % (user.first_name,
                                                user.last_name,
                                                user.email)
                                for user in section.students()     ]

        if len(self.recipients) > 0:
            self.send = True

    def process_mailman(self, user, class_id, section_num, user_type):
        if not (settings.USE_MAILMAN and 'mailman_moderator' in settings.DEFAULT_EMAIL_ADDRESSES.keys()):
            return
        try:
            cls = ClassSubject.objects.get(id=int(class_id))
            section = filter(lambda s: s.index() == int(section_num), cls.sections.all())[0]
        except:
            return

        # Create a section list in Mailman,
        # then bounce this e-mail off to it

        list_name = "%s-%s" % (section.emailcode(), user_type)

        create_list(list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])
        load_list_settings(list_name, "lists/class_mailman.config")

        if user_type != "teachers":
            add_list_member(list_name, ["%s %s <%s>" % (x.first_name, x.last_name, x.email, ) for x in section.students()])

            apply_list_settings(list_name, {'moderator': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], '%s-teachers@%s' % (cls.emailcode(), Site.objects.get_current().domain)]})
            if DEBUG: print "Settings applied..."
            send_mail("[ESP] Activated class mailing list: %s@%s" % (list_name, Site.objects.get_current().domain),
                      render_to_string("mailman/new_list_intro_teachers.txt", 
                                       { 'classname': str(cls),
                                         'mod_password': set_list_moderator_password(list_name) }),
                      settings.DEFAULT_EMAIL_ADDRESSES['default'], ["%s-teachers@%s" % (cls.emailcode(), Site.objects.get_current().domain), ])
        else:
            apply_list_settings(list_name, {'default_member_moderation': False})
            apply_list_settings(list_name, {'generic_nonmember_action': 0})
            apply_list_settings(list_name, {'acceptable_aliases': "%s.*-(students|class)-.*@%s" % (cls.emailcode(), Site.objects.get_current().domain)})

        if DEBUG: print "Settings applied still..."
        add_list_member(list_name, [cls.parent_program.director_email])
        add_list_member(list_name, [x.email for x in cls.teachers()])
        if 'archive' in settings.DEFAULT_EMAIL_ADDRESSES:
            add_list_member(list_name, settings.DEFAULT_EMAIL_ADDRESSES['archive'])
        if DEBUG: print "Members added"

        self.recipients = ["%s@%s" % (list_name, Site.objects.get_current().domain)]
        self.send = True

