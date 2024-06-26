from __future__ import absolute_import
import datetime
import subprocess

from django.db.models.aggregates import Count, Min
from django.db.models.query import Q

from argcache import cache_function_for, cache_function
from esp.program.models import ClassSection
from esp.program.models import StudentSubjectInterest, StudentRegistration
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.users.models import Record
from esp.utils.web import render_to_response
import six
from six.moves import zip


class BigBoardModule(ProgramModuleObj):
    doc = """Shows statistics about student registration that refresh automatically."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Registration Big Board",
            "link_title": "Watch incoming student registrations",
            "module_type": "manage",
            "seq": 10,
            "choosable": 1,
            }

    class Meta:
        proxy = True
        app_label = 'modules'

    @main_call
    @needs_admin
    def bigboard(self, request, tl, one, two, module, extra, prog):
        """Loads a few numbers about student registration.

        This may be loaded by a bunch of admins at once and refreshed quickly,
        at a time when the website is already slow, so it needs to be really
        fast.
        """
        # Most of the numbers on the page are rendered from this list, which
        # should consist of pairs (description, number)
        numbers = [
            ("students registering in the last 10 minutes",
             self.num_active_users(prog)),
            ("students checked in",
             self.num_checked_in_users(prog)),
            ("students with lottery preferences",
             self.num_users_with_lottery(prog)),
            ("students enrolled in a class",
             self.num_users_enrolled(prog)),
            ("students who completed the medical form",
             self.num_medical(prog)),
            ("first choices entered",
             self.num_priority1s(prog)),
            ("stars entered",
             self.num_ssis(prog)),
            ("lottery preferences entered",
             self.num_prefs(prog)),
        ]

        numbers = [(desc, num) for desc, num in numbers if num]

        timess = [
            ("completed the medical form", [(1, time) for time in self.times_medical(prog)], True),
            ("set class lottery preferences", [(1, time) for time in self.times_lottery(prog)], True),
            ("enrolled in classes", [(1, time) for time in self.times_enrolled(prog)], True),
        ]

        timess_data, start = self.make_graph_data(timess, 4, 0, 5)

        left_axis_data = [
            {"axis_name": "#", "series_data": timess_data},
        ]

        context = {
            "type": "Student",
            "numbers": numbers,
            "popular_classes": self.popular_classes(prog),
            "first_hour": start,
            "left_axis_data": left_axis_data,
            "loads": list(zip([1, 5, 15], self.load_averages())),
            "timeslots": prog.getTimeSlots(),
            "categories": prog.class_categories.all().order_by('category').values_list("symbol", flat = True)
        }
        return render_to_response(self.baseDir()+'bigboard.html',
                                  request, context)

    # Numbers computed for the big board are below.  They're cached for 105
    # seconds, which is long enough that they hopefully won't get recomputed a
    # bunch if multiple admins are loading the page, but short enough that each
    # time the page refreshes for the same admin, they will get new numbers

    @cache_function_for(105)
    def users_enrolled(prog):
        # Querying for SRs and then extracting the users saves us joining the
        # users table.
        return StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=prog,
            relationship__name='Enrolled'
        ).values_list('user', flat = True).distinct()
    users_enrolled = staticmethod(users_enrolled)

    @cache_function_for(105)
    def num_users_enrolled(self, prog):
        return self.users_enrolled(prog).count()

    @cache_function_for(105)
    def users_with_lottery(prog):
        # Past empirical observation has shown that doing the union in SQL is
        # much, much slower for unknown reasons; it also means we would have to
        # query over the users table, so this saves us joining that table.
        users_with_ssis = set(
            StudentSubjectInterest.valid_objects()
            .filter(subject__parent_program=prog)
            .values_list('user', flat = True).distinct())
        users_with_srs = set(
            StudentRegistration.valid_objects()
            .filter(
                Q(relationship__name='Interested') |
                Q(relationship__name__contains='Priority/'),
                section__parent_class__parent_program=prog)
            .values_list('user', flat = True).distinct())
        return users_with_ssis | users_with_srs
    users_with_lottery = staticmethod(users_with_lottery)

    @cache_function_for(105)
    def num_users_with_lottery(self, prog):
        return len(self.users_with_lottery(prog))

    @cache_function_for(105)
    def num_active_users(self, prog, minutes=10):
        recent = datetime.datetime.now() - datetime.timedelta(0, minutes * 60)
        users_with_ssis = set(
            StudentSubjectInterest.objects
            .filter(subject__parent_program=prog)
            .filter(start_date__gt=recent)
            .values_list('user').distinct())
        users_with_srs = set(
            StudentRegistration.objects
            .filter(section__parent_class__parent_program=prog)
            .filter(start_date__gt=recent)
            .values_list('user').distinct())
        users_with_meds = set(
            Record.objects
            .filter(program=prog, event__name__in=['med', 'med_bypass'])
            .filter(time__gt=recent)
            .values_list('user').distinct())
        return len(users_with_ssis | users_with_srs | users_with_meds)

    @cache_function_for(105)
    def num_ssis(self, prog):
        return StudentSubjectInterest.valid_objects().filter(
            subject__parent_program=prog).count()

    @cache_function_for(105)
    def num_priority1s(self, prog):
        return StudentRegistration.valid_objects().filter(
            relationship__name='Priority/1',
            section__parent_class__parent_program=prog).count()

    @cache_function_for(105)
    def num_prefs(self, prog):
        num_srs = StudentRegistration.valid_objects().filter(
            Q(relationship__name='Interested') |
            Q(relationship__name__contains='Priority/'),
            section__parent_class__parent_program=prog).count()
        return num_srs + self.num_ssis(prog)

    @cache_function_for(105)
    def num_medical(self, prog):
        return Record.objects.filter(program=prog,
                                     event__name__in=['med', 'med_bypass']).count()

    @cache_function_for(105)
    def checked_in_users(prog):
        return Record.objects.filter(program=prog, event__name='attended').values_list('user', flat = True).distinct()
    checked_in_users = staticmethod(checked_in_users)

    @cache_function_for(105)
    def num_checked_in_users(self, prog):
        return self.checked_in_users(prog).count()

    @cache_function_for(105)
    def popular_classes_wrapper(self, prog):
        # this caches this based on time, so even if the dependencies are updated,
        # we only update the cache every 105 seconds
        return self.popular_classes(prog)

    @cache_function
    def popular_classes(self, prog):
        # this caches this based on dependencies, so even if the 105 second
        # timer runs out, we only update if the dependencies have changed
        sections = ClassSection.objects.filter(
            parent_class__parent_program=prog).exclude(parent_class__category__category='Lunch')
        fields = [
            ("number of stars", 'parent_class__studentsubjectinterest', sections),
            ("number of first choices", 'studentregistration',
             sections.filter(studentregistration__relationship__name='Priority/1')),
            ("number of enrollments", "studentregistration",
             sections.filter((Q(studentregistration__start_date=None) | Q(studentregistration__start_date__lte=datetime.datetime.now())) &
                 (Q(studentregistration__end_date=None) | Q(studentregistration__end_date__gte=datetime.datetime.now())) &
                 Q(studentregistration__relationship__name='Enrolled'))),
        ]
        popular_classes = []
        for description, field, qs in fields:
            qs = qs.annotate(points=Count(field)).values('id', 'points',
            ).exclude(points__lte=0).order_by('-points')
            # The above query should Just Work, but django does something
            # suboptimal in query generation: even though only
            # section.id and the COUNT() are in the SELECT
            # clause, all columns of section get put into the GROUP BY
            # clause.
            #
            # Ideally we would only put it section.id, but
            # SQL won't like that, since other fields appear in the SELECT
            # clause, but we can just put in those fields.  It turns out this
            # minor change increases performance a lot because it saves having
            # to do the GROUP BY on disk.  This increases the overall
            # performance from ~10s to ~50ms on my dev server for MIT Spark
            # 2014.  Note that on my dev server, the query still has to page to
            # disk on for MIT Splash 2013, but on esp.mit.edu, it doesn't --
            # presumably postgres has more memory there.
            #
            # Luckily, we don't have to write the entire query from scratch to
            # fix this: we can just edit QuerySet.query.group_by to remove the
            # unnecessary fields, and django will generate the right query.
            #
            # TODO(benkraft): Once we're on django 1.5, if we need to we can
            # make this even a little better.  SQL always wants to GROUP BY on
            # all non-aggregate fields in the SELECT, even if we know that one
            # of them is unique.  So in fact if we were to
            #   SELECT MAX(program_class.title) AS title, ...
            # we could remove program_class.title from the GROUP BY (and
            # likewise for program_classcategories.symbol), and hopefully make
            # this fast even of a dev server.  This would consist roughly of
            # adding title_=Max('title') to the annotate clause and changing
            # 'title' to 'title_' in values(), and likewise for
            # 'category__symbol'.
            qs.query.group_by = [column for column in qs.query.group_by
                                 if column in qs.query.select]
            qs_list = list(qs)
            if len(qs_list)>0:
                series = []
                timeslots = prog.getTimeSlots()
                for sec in qs_list:
                    sec_obj = ClassSection.objects.get(id=sec['id'])
                    sec_dict = {'name': sec_obj, 'data': []}
                    mts = sec_obj.meeting_times.all()
                    sec_dict['data'] = [[ts.start, sec['points']] for ts in timeslots if ts in mts]
                    series.append(sec_dict)
                popular_classes.append((description, series))
        return popular_classes
    popular_classes.depend_on_row(StudentRegistration, lambda sr: {'prog': sr.section.parent_class.parent_program},
                                                       filter = lambda sr: (sr.relationship.name in ["Priority/1", "Enrolled"]))
    popular_classes.depend_on_row(StudentSubjectInterest, lambda ssi: {'prog': ssi.subject.parent_program})

    @cache_function_for(105)
    def times_medical(self, prog):
        return list(
            Record.objects
            .filter(program=prog, event__name__in=('med', 'med_bypass'))
            .values('user').annotate(Min('time'))
            .order_by('time__min').values_list('time__min', flat=True))

    @cache_function_for(105)
    def times_lottery(self, prog):
        # stars or priorities
        ssi_times_dict = dict(
            StudentSubjectInterest.objects.filter(subject__parent_program=prog)
            # GROUP BY user, SELECT user and min start date.
            # Don't you love django ORM syntax?
            .values_list('user').annotate(Min('start_date')))
        sr_times = StudentRegistration.objects.filter(
            section__parent_class__parent_program=prog, relationship__name__startswith="Priority"
        ).values_list('user').annotate(Min('start_date'))
        for id, sr_time in sr_times:
            if id not in ssi_times_dict or sr_time < ssi_times_dict[id]:
                ssi_times_dict[id] = sr_time
        return sorted(six.itervalues(ssi_times_dict))

    @cache_function_for(105)
    def times_enrolled(self, prog):
        # we don't use valid_objects() here because we want to know exactly when each user first
        # enrolled in a class, even if they aren't enrolled in that class anymore; however,
        # this also means that the final number here might not match that from users_enrolled()
        return list(
            StudentRegistration.objects
            .filter(section__parent_class__parent_program=prog, relationship__name="Enrolled")
            .values('user').annotate(Min('start_date'))
            .order_by('start_date__min').values_list('start_date__min', flat=True))

    @staticmethod
    def chunk_times(times, start, end, delta=datetime.timedelta(0, 3600), cumulative = True):
        """Given a list of times, return hourly summaries.

        `times` should be a list of tuples, sorted by time, containing some metric (duration, capacity, etc.) and datetime.datetime objects
        `start` and `end` should be datetimes; the chunks will be for hours between them, inclusive.
        `cumulative` should be a boolean determining whether counts should be summed cumulatively for conseculative hours or if they should only be summed within individual hours
        Returns a list of integers, each of which is the number of times that
        precede the given hour.
        """
        # Round down to the nearest hour.
        chunks = []
        i = 0
        count = 0
        # Unpythonic, I know.  Iterating over hours is annoying, and we're also
        # iterating over timestamps at the same time.
        while start < end + delta:
            if i < len(times) and times[i][1] < start:
                # If this time is in the hour we're currently processing, just
                # go to the next time.
                count += times[i][0]
                i += 1
            else:
                # Otherwise, move to the next hour, and save the number of
                # times preceding it for the previous hour.
                chunks.append(float(count))
                start += delta
                if not cumulative:
                    count = 0
        return chunks

    @staticmethod
    def make_graph_data(timess, drop_beg = 0, drop_end = 0, cutoff = 1):
        """Given a list of time series, return graph data series.

        `timess` should be a list of tuples (description, sorted tuples of metrics and datetime.datetime objects, whether counts should be cumulative).
        `drop_beg` should be a number of items to drop from the beginning of each list
        `drop_end` should be a number of items to drop from the end of each list
        `cutoff` should be the minimum number of items that must exist in a time series

        Returns a dict of cleaned time series and the start time for graphing
        """
        #Remove any time series without at least 'cutoff' times
        timess = [(desc, times, cumulative) for desc, times, cumulative in timess if len(times) >= cutoff]
        # Drop the first and last times if specified
        # Then round start down and end up to the nearest day.
        if not timess:
            graph_data = []
            start = None
        else:
            start = min([times[drop_beg:(len(times)-drop_end)][0][1] for desc, times, cumulative in timess])
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = max([times[drop_beg:(len(times)-drop_end)][-1][1] for desc, times, cumulative in timess])
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)
            end += datetime.timedelta(1)
            end = min(end, datetime.datetime.now())
            graph_data = [{"description": desc,
                           "data": BigBoardModule.chunk_times(times, start, end, cumulative = cumulative)}
                          for desc, times, cumulative in timess]
        return graph_data, start

    # runs in 9ms, so don't bother caching
    def load_averages(self):
        try:
            uptime = subprocess.check_output('uptime')
            # The output ends in e.g. "load average: 1.65, 1.84, 1.67\n"
            return [float(x.strip(',')) for x in uptime.strip().split()[-3:]]
        except:
            return []

    def isStep(self):
        return False
