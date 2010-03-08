from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject, ClassSection
from esp.mailman import create_list, load_list_settings, add_list_member, set_list_moderator_password, apply_list_settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

DEBUG=True
DEBUG=False

class SectionList(BaseHandler):

    def process(self, user, class_id, section_num, user_type):
        try:
            cls = ClassSubject.objects.get(id=int(class_id))
            section = filter(lambda s: s.index() == int(section_num), cls.sections.all())[0]
        except:
            return

        # Create a section list in Mailman,
        # then bounce this e-mail off to it

        list_name = "%s-%s" % (section.emailcode(), user_type)

        create_list(list_name, "esp-moderators@mit.edu")
        load_list_settings(list_name, "lists/class_mailman.config")

        if user_type != "teachers":
            add_list_member(list_name, ["%s %s <%s>" % (x.first_name, x.last_name, x.email, ) for x in section.students()])

            apply_list_settings(list_name, {'moderator': ['esp-moderators@mit.edu', '%s-teachers@esp.mit.edu' % cls.emailcode()]})
            if DEBUG: print "Settings applied..."
            send_mail("[ESP] Activated class mailing list: %s@esp.mit.edu", 
                      render_to_string("mailman/new_list_intro_teachers.txt", 
                                       { 'classname': str(cls),
                                         'mod_password': set_list_moderator_password(list_name) }),
                      "esp@mit.edu", ["%s-teachers@esp.mit.edu" % cls.emailcode(), ])
        else:
            apply_list_settings(list_name, {'default_member_moderation': False})
            apply_list_settings(list_name, {'generic_nonmember_action': 0})

        if DEBUG: print "Settings applied still..."
        add_list_member(list_name, [cls.parent_program.director_email])
        add_list_member(list_name, [x.email for x in cls.teachers()])
        if DEBUG: print "Members added"

        self.recipients = ["%s@esp.mit.edu" % list_name]
        self.send = True

