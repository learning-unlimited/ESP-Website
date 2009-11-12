from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject, ClassSection
from esp.mailman import create_list, load_list_settings, add_list_member

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
        load_list_settings(list_name, "esp/mailman/sample_config.mailman")

        add_list_member(list_name, cls.parent_program.director_email)
        add_list_member(list_name, [x.email for x in cls.teachers()])

        if user_type != "teachers":
            add_list_member(list_name, [x.email for x in section.students()])

        self.recipients = ["%s@esp.mit.edu" % list_name]
        self.send = True

