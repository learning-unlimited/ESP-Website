import datetime
import subprocess

from django.db.models.aggregates import Min, Sum
from django.db.models.query import Q
from django.db.models import Count

from argcache import cache_function_for
from esp.program.models import ClassSubject, ClassSection
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
            "seq": 11,
            "choosable": 1,
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
        approved_hours_stats = self.static_hours(prog, True)
        numbers = [
            ("teachers registering in the last 10 minutes",
             self.num_active_users(prog)),
            ("teachers with a class registered",
             self.num_teachers_teaching(prog)),
            ("teachers with a class approved",
             self.num_teachers_teaching(prog, True)),
            ("classes registered",
             self.num_class_reg(prog)),
            ("classes approved",
             self.num_class_reg(prog, True)),
            ("class-hours registered",
             hours_stats[0]),
            ("class-hours approved",
             approved_hours_stats[0]),
            ("class-student-hours registered",
             hours_stats[1]),
            ("class-student-hours approved",
             approved_hours_stats[1]),
            ("teachers checked in today",
             self.num_checked_in_teachers(prog)),
        ]

        numbers = [(desc, num) for desc, num in numbers if num]

        # if there are any classes without a timestamp, don't even bother calculating the graph data
        if ClassSubject.objects.filter(parent_program=prog, timestamp__isnull=True).exists():
            timess_data = []
            class_hourss_data = []
            student_hourss_data = []
            start = self.mindate
        else:
            timess = [
                ("number of registered classes", [(1, time) for time in self.reg_classes(prog)], True),
                ("number of approved classes", [(1, time) for time in self.reg_classes(prog, True)], True),
                ("number of teachers registered", [(1, time) for time in self.teach_times(prog)], True),
                ("number of teachers approved", [(1, time) for time in self.teach_times(prog, True)], True),
            ]

            timess_data, start = BigBoardModule.make_graph_data(timess)

            class_hours, student_hours = self.get_hours(prog)
            class_hours_approved, student_hours_approved = self.get_hours(prog, approved = True)

            class_hourss = [
                ("number of registered class-hours", class_hours, True),
                ("number of approved class-hours", class_hours_approved, True),
            ]
            class_hourss_data, _ = BigBoardModule.make_graph_data(class_hourss)

            student_hourss = [
                ("number of registered class-student-hours", student_hours, True),
                ("number of approved class-student-hours", student_hours_approved, True),
            ]
            student_hourss_data, _ = BigBoardModule.make_graph_data(student_hourss)

        left_axis_data = [
            {"axis_name": "#", "series_data": timess_data},
        ]
        right_axis_data = [
            {"axis_name": "class-hours", "series_data": class_hourss_data},
            {"axis_name": "class-student-hours", "series_data": student_hourss_data},
        ]

        context = {
            "type": "Teacher",
            "numbers": numbers,
            "first_hour": start,
            "left_axis_data": left_axis_data,
            "right_axis_data": right_axis_data,
            "loads": zip([1, 5, 15], self.load_averages()),
        }
        return render_to_response('program/modules/bigboardmodule/bigboard.html',
                                  request, context)

    # Numbers computed for the big board are below.  They're cached for 105
    # seconds, which is long enough that they hopefully won't get recomputed a
    # bunch if multiple admins are loading the page, but short enough that each
    # time the page refreshes for the same admin, they will get new numbers

    # this is the date we added timestamps
    mindate = datetime.datetime(2016, 1, 30)

    @cache_function_for(105)
    def num_teachers_teaching(self, prog, approved = False):
        # Querying for SRs and then extracting the users saves us joining the
        # users table.
        return ClassSubject.objects.filter(self.get_filter(prog, approved)
        ).exclude(category__category__iexact="Lunch"
        ).exclude(teachers=None
        ).values_list('teachers').distinct().count()

    @cache_function_for(105)
    def num_active_users(self, prog, minutes=10):
        recent = datetime.datetime.now() - datetime.timedelta(0, minutes * 60)
        return ClassSubject.objects.filter(parent_program=prog, timestamp__gt=recent
        ).exclude(category__category__iexact="Lunch"
        ).exclude(teachers=None
        ).values_list('teachers').distinct().count()

    @cache_function_for(105)
    def num_checked_in_teachers(self, prog):
        now = datetime.datetime.now()
        return Record.objects.filter(program=prog, event='teacher_checked_in',
            time__year=now.year,
            time__month=now.month,
            time__day=now.day).count()

    @cache_function_for(105)
    def num_class_reg(self, prog, approved = False):
        return ClassSubject.objects.filter(self.get_filter(prog, approved)
        ).exclude(category__category__iexact="Lunch").distinct().count()

    @cache_function_for(105)
    def reg_classes(self, prog, approved = False):
        class_times = ClassSubject.objects.filter(self.get_filter(prog, approved)
        ).exclude(category__category__iexact="Lunch"
        ).distinct().values_list('timestamp', flat=True)
        return sorted(class_times)

    @cache_function_for(105)
    def teach_times(self, prog, approved = False):
        teacher_times = dict(ClassSubject.objects.filter(self.get_filter(prog, approved)
        ).exclude(category__category__iexact="Lunch"
        ).exclude(teachers=None
        ).distinct().values_list('teachers').annotate(Min('timestamp')))
        return sorted(teacher_times.itervalues())

    @cache_function_for(105)
    def get_hours(self, prog, approved = False):
        hours = ClassSubject.objects.filter(self.get_filter(prog, approved)
        ).annotate(num_sections=Count('sections')).filter(num_sections__gt=0
        ).exclude(category__category__iexact="Lunch"
        ).values_list('timestamp','class_size_max'
        ).annotate(duration=Sum('sections__duration'))
        # use mindate if a class is missing a timestamp so we can still calculate static stats
        sorted_hours = sorted(hours, key=lambda x:x[0] or self.mindate)
        class_hours = [(hour[2],hour[0]) for hour in sorted_hours]
        student_hours = [(hour[2]*hour[1], hour[0]) for hour in sorted_hours]
        return class_hours, student_hours

    @cache_function_for(105)
    def static_hours(self, prog, approved = False):
        hours = self.get_hours(prog, approved)
        if hours[0]:
            return [sum(zip(*j)[0]) for j in hours]
        else:
            return [0,0]

    @staticmethod
    def get_filter(prog, approved):
        filt = Q(parent_program=prog)
        if approved:
            filt &= Q(status__gt=0, sections__status__gt=0)
        return filt

    # runs in 9ms, so don't bother caching
    def load_averages(self):
        try:
            uptime = subprocess.check_output('uptime')
            # The output ends in e.g. "load average: 1.65, 1.84, 1.67\n"
            return [float(x.strip(',')) for x in uptime.strip().split()[-3:]]
        except:
            return []
