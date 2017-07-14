import datetime
import operator
import subprocess

from django.db.models.aggregates import Count, Max, Min
from django.db.models.query import Q

from argcache import cache_function_for
from esp.program.models import ClassSubject
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.users.models import Record
from esp.utils.decorators import cached_module_view
from esp.utils.web import render_to_response
from esp.program.modules.handlers.bigboardmodule import BigBoardModule


class TeacherBigBoardModule(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Registration Big Board",
            "link_title": "Watch incoming teacher registrations",
            "module_type": "manage",
            "seq": 11
            }

    class Meta:
        proxy = True
        app_label = 'modules'

    @main_call
    @needs_admin
    def teacherbigboard(self, request, tl, one, two, module, extra, prog):
        """Loads a few numbers about teacher registration.

        This may be loaded by a bunch of admins at once and refreshed quickly,
        at a time when the website is already slow, so it needs to be really
        fast.
        """
        # Most of the numbers on the page are rendered from this list, which
        # should consist of pairs (description, number)
        hours_stats = self.static_hours(prog)
        numbers = [
            ("teachers registering in the last 10 minutes",
             self.num_active_users(prog)),
            ("teachers teaching a class",
             self.num_teachers_teaching(prog)),
            ("classes registered",
             self.num_class_reg(prog)),
            ("classes approved",
             self.num_class_app(prog)),
            ("class-hours registered",
             hours_stats[0]),
            ("class-student-hours registered",
             hours_stats[1]),
            ("teachers checked in today",
             self.num_checked_in_teachers(prog)),
        ]

        numbers = [(desc, num) for desc, num in numbers if num]

        timess = [
            ("number of registered classes", self.reg_classes(prog)),
            ("number of approved classes", self.app_classes(prog)),
            ("number of teachers teaching", self.teach_times(prog)),
        ]

        graph_data, start = BigBoardModule.make_graph_data(timess)

        hourss = self.get_hours(prog)

        class_hours, student_hours = self.make_hours_data(hourss)
        graph_data.append(class_hours)

        context = {
            "type": "Teacher",
            "numbers": numbers,
            "first_hour": start,
            "graph_data": graph_data,
            "student_hours": student_hours,
            "loads": zip([1, 5, 15], self.load_averages()),
        }
        return render_to_response('program/modules/bigboardmodule/bigboard.html',
                                  request, context)

    # Numbers computed for the big board are below.  They're cached for 105
    # seconds, which is long enough that they hopefully won't get recomputed a
    # bunch if multiple admins are loading the page, but short enough that each
    # time the page refreshes for the same admin, they will get new numbers

    @cache_function_for(105)
    def num_teachers_teaching(self, prog):
        # Querying for SRs and then extracting the users saves us joining the
        # users table.
        return ClassSubject.objects.filter(parent_program=prog
        ).values_list('teachers').distinct().count()

    @cache_function_for(105)
    def num_active_users(self, prog, minutes=10):
        recent = datetime.datetime.now() - datetime.timedelta(0, minutes * 60)
        return ClassSubject.objects.filter(parent_program=prog, timestamp__gt=recent
        ).values_list('teachers').distinct().count()

    @cache_function_for(105)
    def num_checked_in_teachers(self, prog):
        return Record.objects.filter(program=prog, event='teacher_checked_in').count()

    @cache_function_for(105)
    def num_class_reg(self, prog):
        return ClassSubject.objects.filter(parent_program=prog).values_list('id').count()

    @cache_function_for(105)
    def num_class_app(self, prog):
        return ClassSubject.objects.filter(parent_program=prog, status__gt=0, sections__status__gt=0).count()

    @cache_function_for(105)
    def reg_classes(self, prog):
        class_times = dict(ClassSubject.objects.filter(parent_program=prog
        ).values_list('id').annotate(Min('timestamp')))
        return sorted(class_times.itervalues())

    @cache_function_for(105)
    def app_classes(self, prog):
        #all ClassSubjects that are approved (and have an approved section)
        class_times = dict(ClassSubject.objects.filter(parent_program=prog, status__gt=0, sections__status__gt=0
        ).values_list('id').annotate(Min('timestamp')))
        return sorted(class_times.itervalues())

    @cache_function_for(105)
    def teach_times(self, prog):
        teacher_times = dict(ClassSubject.objects.filter(parent_program=prog
        ).values_list('teachers').annotate(Min('timestamp')))
        return sorted(teacher_times.itervalues())

    @cache_function_for(105)
    def get_hours(self, prog):
        hours = ClassSubject.objects.filter(parent_program=prog
        ).exclude(category__category__iexact="Lunch").values_list('id','duration','class_size_max'
        ).annotate(Min('timestamp'))
        sorted_hours = sorted(hours, key=operator.itemgetter(2))
        return [hour[1:] for hour in sorted_hours]

    @cache_function_for(105)
    def static_hours(self, prog):
        hours = ClassSubject.objects.filter(parent_program=prog
        ).exclude(category__category__iexact="Lunch").values_list('id','duration','class_size_max'
        )
        hours = [[float(j[1])] + [float(j[1])*j[2]] for j in hours]
        return [sum(j) for j in zip(*hours)]

    @staticmethod
    def make_hours_data(hourss, drop_beg = 0, drop_end = 0, cutoff = 0, delta=datetime.timedelta(0, 3600)):
        """Given a dict of time series, return graph data series.

        `hourss` should be a list of class tuples, sorted by time, containing duration, capacity, and datetime.datetime objects
        `drop_beg` should be a number of items to drop from the beginning of each list
        `drop_end` should be a number of items to drop from the end of each list
        `cutoff` should be the minimum number of items that must exist in a time series

        Returns a dict of cleaned time series and the start time for graphing
        """
        if not len(hourss) >= cutoff:
            hours_data = []
        else:
            start = min([hours[drop_beg:(len(hours)-drop_end)][2] for hours in hourss])
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = max([hours[drop_beg:(len(hours)-drop_end)][2] for hours in hourss])
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)
            end += datetime.timedelta(1)
            end = min(end, datetime.datetime.now())

        class_hours = []
        student_hours = []
        i = 0
        hours_c = 0
        hours_s = 0
        # Unpythonic, I know. Iterating over hours is annoying, and we're also
        # iterating over timestamps at the same time.
        while start < end + delta:
            if i < len(hourss) and hourss[i][2] < start:
                # If this time is in the hour we're currently processing, just
                # go to the next time.
                hours_c += hourss[i][0]
                hours_s += hourss[i][0] * hourss[i][1]
                i += 1
            else:
                # Otherwise, move to the next hour, and save the number of
                # times preceding it for the previous hour.
                class_hours.append(float(hours_c))
                student_hours.append(float(hours_s))
                start += delta

        hours_data = [{"description": "number of registered class-hours",
                       "data": class_hours},
                      {"description": "number of registered class-student-hours",
                       "data": student_hours}]
        return hours_data

    # runs in 9ms, so don't bother caching
    def load_averages(self):
        try:
            uptime = subprocess.check_output('uptime')
            # The output ends in e.g. "load average: 1.65, 1.84, 1.67\n"
            return [float(x.strip(',')) for x in uptime.strip().split()[-3:]]
        except:
            return []
