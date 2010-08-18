from django.db import models
from esp.program.models import Program, ClassSection
from esp.program.views import find_user as auto_find_user
from esp.users.models import ESPUser
from esp.db.fields import AjaxForeignKey
from esp.datatree.models import GetNode
from esp.cal.models import Event, EventType
from esp.utils.memoize import lru_cache

from datetime import date, time, datetime, timedelta
from parsedatetime.parsedatetime import Calendar

import re

ClassIdRegex = re.compile(r"^[A-Z]([0-9]*)")
ClassSectionRegex = re.compile(r"^[A-Z]([0-9]*)s([0-9]*)")

class Attendance(models.Model):
    program = AjaxForeignKey(Program)
    class_section = AjaxForeignKey(ClassSection, null=True)
    user = AjaxForeignKey(ESPUser)
    date = AjaxForeignKey(Event)
    status = models.CharField(max_length=16, default='Attended')

    @staticmethod
    def find_user(user_name):
        retVal = auto_find_user(user_name)
        if retVal:
            return retVal
        raise ESPUser.DoesNotExist

    @lru_cache(1)
    @staticmethod
    def find_program(prog_name):
        """
        Find the Program object for the named program
        prog_name must either be a program ID# or the exact string name of a registered program.
        """
        try:
            return Program.objects.get(int(prog_name))
        except TypeError:
            pass  ## Nope, we're not lucky; we didn't get an integer ID.

        ## There must be a more efficient way of doing this, but I don't know it...
        ## At least order by ID, since we're most likely to see data from recent programs

        prog_name_lower = prog_name.lower()
        for p in Program.objects.all().select_related('anchor', 'anchor__parent').order_by('-id'):
            if prog_name_lower in p.niceName().lower():
                return p

        raise Program.DoesNotExist

    @staticmethod
    def find_class(class_name, prog = None):
        """
        Find the class with the specified name
        The name must be in catalog form, ie., 'A1234s1: My Class'
        """
        ## This one's ideally a lot easier:  Class names are spec'ed as being in catalog form; "ID: name"
        section = ClassSectionRegex.match(class_name)
        if sections:
            cls_id, sec_num = section.groups()
            if prog:
                return ClassSection.objects.get(parent_class__id=cls_id, anchor__name="Section%s" % sec_num, parent_class__parent_program=prog)
            else:
                return ClassSection.objects.get(parent_class__id=cls_id, anchor__name="Section%s" % sec_num)
            
        cls = ClassIdRegex.match(class_name)
        if cls:
            cls_id, = section.groups()
            if prog:
                return ClassSection.objects.get(parent_class__id=cls_id, parent_class__parent_program=prog)
            else:
                return ClassSection.objects.get(parent_class__id=cls_id)

        ## Well, that failed.  Give it one more go, the brute-force way:
        if prog:
            return ClassSection.objects.get(parent_class__name__icontains=class_name, parent_class__parent_program=prog)
        else:
            return ClassSection.objects.get(parent_class__name__icontains=class_name)

    @staticmethod
    def find_timeblock(timeblock, prog = None, cls = None, create = True, default_duration = timedelta(0,3600)):
        """
        Find an Event corresponding to the specified time
        Create one if one doesn't exist and if create == True
        'timeblock' must be either a datetime.datetime instance,
        or a string representing a date/time, as parseable by the
        'parsedatetime' module.
        """
        if isinstance(timeblock, Event):
            ## You're silly, now, aren't you?
            return timeblock
        
        if not isinstance(timeblock, datetime):
            c = parsedatetime.Calendar()
            timeblock_struct, result = c.parse(timeblock)
            if result == 0:
                raise TypeError
            elif result == 1:
                timeblock = date(timeblock_struct[:3])
            elif result == 2:
                timeblock = time(timeblock_struct[3:6])
            elif result == 3:
                timeblock = datetime(timeblock_struct[:6])
            else:
                assert False, "Internal Error, invalid parsedatetime response code: '%s'" % (str(result))

        try:
            Event.objects.get(start=timeblock)
        except Event.DoesNotExist:
            if create:
                event_args = {}

                if cls:
                    ## If we know the class, we know of an even better tree anchor
                    event_args['anchor'] = GetNode(cls.anchor.uri + "/Attendance")
                elif prog:
                    ## If we know the program, we know of a better tree anchor
                    event_args['anchor'] = GetNode(prog.anchor.uri + "/Attendance")
                else:
                    ## Nope. Generic anchor time.
                    event_args['anchor'] = GetNode("Q/Attendance/TimeBlock")

                event_args['start'] = start
                event_args['end'] = start + default_duration

                event_args['short_description'] = str(start) + " to " + str(event_args['end'])
                event_args['description'] = str(cls) + ': ' + event_args['short_description']

                event_args['event_type'] = EventType.objects.get_or_create(description='Class Time Block')[0]

                return Event.objects.create(**event_args)

        raise Event.DoesNotExist


    @classmethod
    def log_attendance(cls, prog_name, cls_name, user_name, timeblock_name, status = 'Attended'):
        """
        Mark the specified user as having attended (or not) the specified program/class at the specified time.
        Note that non-attendance does not need to be logged at all; it is the default state.
        if cls_name is None, don't mark the attendance as per-class.
        """
        prog = cls.find_program(prog_name)
        if cls_name:
            section = cls.find_class(cls_name)
        user = cls.find_user(user_name)
        timeblock = cls.find_timeblock(timeblock_name)

        if cls_name:
            cls.create(program=prog, class_section=section, user=user, date=timeblock, status=status)
        else:
            cls.create(program=prog, user=user, date=timeblock, status=status)
