from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject, ClassSection
from esp.mailman import create_list, load_list_settings, add_list_member

class ClassList(BaseHandler):

    def process(self, user, class_id, user_type):
        try:
            cls = ClassSubject.objects.get(id = class_id)
            sections = cls.sections.all()
        except ESPUser.DoesNotExist:
            return

        # Create a section list in Mailman,
        # then bounce this e-mail off to it

        list_name = "%s-%s" % (cls.emailcode(), user_type)

        create_list(list_name, "esp-moderators@mit.edu")
        load_list_settings(list_name, "esp/mailman/sample_config.mailman")

        add_list_member(list_name, cls.parent_program.director_email)
        add_list_member(list_name, ["%s@esp.mit.edu" % x.username for x in cls.teachers()])

        if user_type != "teachers":
            for section in sections:
                add_list_member(list_name, ["%s@esp.mit.edu" % x.username for x in section.students()])

        self.recipients = ["%s@esp.mit.edu" % list_name]
        self.send = True
