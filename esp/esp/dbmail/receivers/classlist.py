

from esp.dbmail.base import BaseHandler
from esp.users.models import ESPUser
from esp.program.models import Program, Class

class ClassList(BaseHandler):

    def process(self, user, class_id, user_type):
        try:
            cls = Class.objects.get(id = class_id)
        except ESPUser.DoesNotExist:
            return

        self.recipients = []

        user_type = user_type.strip().lower()

        if user_type in ('teachers','class'):
            self.recipients += ['%s %s <%s>' % (user.first_name,
                                                user.last_name,
                                                user.email)
                                for user in cls.teachers()     ]

        if user_type in ('students','class'):
            self.recipients += ['%s %s <%s>' % (user.first_name,
                                                user.last_name,
                                                user.email)
                                for user in cls.students()     ]


        if len(self.recipients) > 0:
            self.send = True
