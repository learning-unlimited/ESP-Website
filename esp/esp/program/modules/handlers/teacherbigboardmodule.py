import datetime
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
        """Loads a few numbers about student registration.

        This may be loaded by a bunch of admins at once and refreshed quickly,
        at a time when the website is already slow, so it needs to be really
        fast.
        """
        # Most of the numbers on the page are rendered from this list, which
        # should consist of pairs (description, number)
        numbers = [
            ("teachers registering in the last 10 minutes",
             self.num_active_users(prog)),
            ("teachers teaching a class",
             self.num_teachers_teaching(prog)),
            ("classes registered",
             self.num_class_reg(prog)),
            ("classes approved",
             self.num_class_app(prog)),
            ("teachers checked in today",
             self.num_checked_in_teachers(prog)),
        ]

        numbers = [(desc, num) for desc, num in numbers if num]

        timess = [
            ("number of registered classes", self.reg_classes(prog)),
            ("number of approved classes", self.app_classes(prog)),
            ("number of teachers teaching", self.teach_times(prog)),
        ]
        timess = [(desc, times) for desc, times in timess]
        # Round start down and end up to the nearest day.  If
        # there aren't many registrations, don't bother with the graph.
        if not timess:
            graph_data = []
            start = None
        else:
            start = min([times[0] for desc, times in timess])
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = max([times[-1] for desc, times in timess])
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)
            end += datetime.timedelta(1)
            end = min(end, datetime.datetime.now())
            graph_data = [{"description": desc,
                           "data": BigBoardModule.chunk_times(times, start, end)}
                          for desc, times in timess]

        context = {
            "type": "Teacher",
            "numbers": numbers,
            "first_hour": start,
            "graph_data": graph_data,
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

    def teach_times(self, prog):
        teacher_times = dict(ClassSubject.objects.filter(parent_program=prog
        ).values_list('teachers').annotate(Min('timestamp')))
        return sorted(teacher_times.itervalues())

    # runs in 9ms, so don't bother caching
    def load_averages(self):
        try:
            uptime = subprocess.check_output('uptime')
            # The output ends in e.g. "load average: 1.65, 1.84, 1.67\n"
            return [float(x.strip(',')) for x in uptime.strip().split()[-3:]]
        except:
            return []
