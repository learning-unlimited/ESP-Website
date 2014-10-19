from django.db.models.aggregates import Count, Max
from django.db.models.query import Q

from esp.cache import cache_function_for
from esp.program.models import ClassSubject
from esp.program.models import StudentSubjectInterest, StudentRegistration
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.users.models import Record
from esp.utils.decorators import cached_module_view
from esp.web.util.main import render_to_response


class BigBoardModule(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Registration Big Board",
            "link_title": "Watch incoming student registrations",
            "module_type": "manage",
            "seq": 10
            }

    @main_call
    # @needs_admin
    def bigboard(self, request, tl, one, two, module, extra, prog):
        """Loads a few numbers about student registration.

        This may be loaded by a bunch of admins at once and refreshed quickly,
        at a time when the website is already slow, so it needs to be really
        fast.
        """
        # Most of the numbers on the page are rendered from this list, which
        # should consist of pairs (description, number)
        numbers = [
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

        context = {
            "numbers": numbers,
            "popular_classes": self.popular_classes(prog),
        }
        return render_to_response(self.baseDir()+'bigboard.html',
                                  request, context)

    # Numbers computed for the big board are below.  They're cached for 105
    # seconds, which is long enough that they hopefully won't get recomputed a
    # bunch if multiple admins are loading the page, but short enough that each
    # time the page refreshes for the same admin, they will get new numbers

    @cache_function_for(105)
    def num_users_enrolled(self, prog):
        # Querying for SRs and then extracting the users saves us joining the
        # users table.
        return StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=prog,
            relationship__name='Enrolled'
        ).values_list('user').distinct().count()

    @cache_function_for(105)
    def num_users_with_lottery(self, prog):
        # Past empirical observation has shown that doing the union in SQL is
        # much, much slower for unknown reasons; it also means we would have to
        # query over the users table, so this saves us joining that table.
        users_with_ssis = set(
            StudentSubjectInterest.valid_objects()
            .filter(subject__parent_program=prog)
            .values_list('user').distinct())
        users_with_srs = set(
            StudentRegistration.valid_objects()
            .filter(
                Q(relationship__name='Interested') |
                Q(relationship__name__contains='Priority/'),
                section__parent_class__parent_program=prog)
            .values_list('user').distinct())
        return len(users_with_ssis | users_with_srs)

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
            section__parent_class__parent_program=prog).count()
        return num_srs + self.num_ssis(prog)

    @cache_function_for(105)
    def num_medical(self, prog):
        return Record.objects.filter(program=prog,
                                     event__in=['med', 'med_bypass']).count()

    @cache_function_for(105)
    def popular_classes(self, prog, num=5):
        classes = ClassSubject.objects.filter(
            parent_program=prog).exclude(category__category='Lunch')
        fields = [
            ("number of stars", 'studentsubjectinterest', classes),
            ("number of first choices", 'sections__studentregistration',
             classes.filter(
                 sections__studentregistration__relationship__name='Priority/1')),
        ]
        popular_classes = []
        for description, field, qs in fields:
            qs = qs.annotate(points=Count(field)).values(
                'id', 'category__symbol', 'title', 'points'
            ).order_by('-points')[:num]
            # The above query should Just Work, but django does something
            # suboptimal in query generation: even though only
            # program_class.id, program_class.title,
            # program_classcategories.symbol, and the COUNT() are in the SELECT
            # clause, all columns of program_class get put into the GROUP BY
            # clause.
            #
            # Ideally we would only put it program_class.id, but
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
            popular_classes.append((description, list(qs)))
        return popular_classes
