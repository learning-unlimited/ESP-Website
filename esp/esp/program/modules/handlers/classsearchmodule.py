from __future__ import absolute_import
import json
import random
import re

from collections import OrderedDict

from django.http import HttpResponseRedirect
from django.db.models import Count
from django.db.models.query import Q

from esp.program.modules.forms.teacherreg import TeacherClassRegForm
from esp.program.modules.base import ProgramModuleObj, main_call, needs_admin
from esp.program.models import RegistrationType
from esp.program.models.class_ import ClassSubject, STATUS_CHOICES
from esp.program.models.flags import ClassFlagType
from esp.resources.models import ResourceType
from esp.tagdict.models import Tag
from esp.utils.query_builder import QueryBuilder, SearchFilter
from esp.utils.query_builder import SelectInput, SelectQInput, ConstantInput, TextInput
from esp.utils.query_builder import OptionalInput, DatetimeInput
from esp.utils.web import render_to_response

# TODO: this won't work right without class flags enabled


class ClassSearchModule(ProgramModuleObj):
    doc = """Search for classes matching certain criteria."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Class Search",
            "link_title": "Search for classes",
            "module_type": "manage",
            "seq": 10,
            "choosable": 1,
        }

    class Meta:
        proxy = True
        app_label = 'modules'

    def query_builder(self):
        flag_types = ClassFlagType.get_flag_types(program=self.program)
        flag_datetime_inputs = [
            OptionalInput(name=t, inner=DatetimeInput(
                field_name='flags__%s_time' % t, english_name=''))
            for t in ['created', 'modified']]
        flag_select_input = SelectInput(
            field_name='flags__flag_type',
            options={str(ft.id): ft.name for ft in flag_types})
        any_flag_input = ConstantInput(Q(flags__isnull=False))
        flag_filter = SearchFilter(name='flag', title='the flag',
                                   inputs=[flag_select_input] +
                                   flag_datetime_inputs)
        any_flag_filter = SearchFilter(name='any_flag', title='any flag',
                                       inputs=[any_flag_input] +
                                       flag_datetime_inputs)

        resource_types = ResourceType.objects.filter(program=self.program)
        resource_value_input = OptionalInput(name="desired value",
            inner=TextInput(field_name='sections__resourcerequest__desired_value', english_name=''))
        resource_select_input = SelectInput(
            field_name='sections__resourcerequest__res_type',
            options={str(rt.id): rt.name for rt in resource_types})
        any_resource_input = ConstantInput(Q(sections__resourcerequest__isnull=False))
        resource_filter = SearchFilter(name='resource', title='the requested resource',
                                   inputs=[resource_select_input] + [resource_value_input])
        any_resource_filter = SearchFilter(name='any_resource', title='any requested resource',
                                       inputs=[any_resource_input])

        categories = list(self.program.class_categories.all())
        if self.program.open_class_registration:
            categories.append(self.program.open_class_category)
        category_filter = SearchFilter(
            name='category', title='the category',
            inputs=[SelectInput(field_name='category',
                                options={str(cat.id): cat.category
                                         for cat in categories})])

        durations = self.program.getDurations()
        duration_filter = SearchFilter(
            name='duration', title='the duration',
            inputs=[SelectInput(field_name='duration',
                                options=OrderedDict([(str(duration[0]), duration[1])
                                        for duration in durations]))])

        grades = self.program.classregmoduleinfo.getClassGrades()
        grade_filter = SearchFilter(
            name='grade', title='grades between X and Y',
            inputs=[SelectQInput(options=OrderedDict([(str(grade), {'title': str(grade), 'Q': Q(grade_max__gte=grade)})
                                                      for grade in grades])),
                    SelectQInput(options=OrderedDict([(str(grade), {'title': str(grade), 'Q': Q(grade_min__lte=grade)})
                                                      for grade in grades]))])

        num_sections = self.program.classregmoduleinfo.allowed_sections_actual
        sections_filter = SearchFilter(
            name='num_sections', title='between X and Y section(s)',
            inputs=[SelectQInput(options=OrderedDict([(str(num), {'title': str(num), 'Q': Q(id__in=ClassSubject.objects.annotate(
                                                                                            num_sections=Count("sections")).filter(
                                                                                            num_sections__gte=num).values_list('id', flat=True))})
                                                      for num in num_sections])),
                    SelectQInput(options=OrderedDict([(str(num), {'title': str(num), 'Q': Q(id__in=ClassSubject.objects.annotate(
                                                                                            num_sections=Count("sections")).filter(
                                                                                            num_sections__lte=num).values_list('id', flat=True))})
                                                      for num in num_sections]))])

        capacities = self.program.classregmoduleinfo.getClassSizes()
        capacity_inputs = None
        capacity_title = ""
        # logic copied from the teacher class registration form
        if self.program.classregmoduleinfo.use_class_size_max:
            capacity_title = "capacity (max)"
            capacity_inputs = [SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(class_size_max__gte=cap)})
                                                                 for cap in capacities])),
                               SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(class_size_max__lte=cap)})
                                                                 for cap in capacities]))]
        elif Tag.getBooleanTag('use_class_size_optimal'):
            if self.program.classregmoduleinfo.use_class_size_optimal:
                capacity_title = "capacity (optimal)"
                capacity_inputs = [SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(class_size_optimal__gte=cap)})
                                                                     for cap in capacities])),
                                   SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(class_size_optimal__lte=cap)})
                                                                     for cap in capacities]))]
            elif self.program.classregmoduleinfo.use_optimal_class_size_range:
                capacity_title = "capacity (optimal range)"
                capacity_inputs = [SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(optimal_class_size_range__range_max__gte=cap)})
                                                                     for cap in capacities])),
                                   SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(optimal_class_size_range__range_min__lte=cap)})
                                                                     for cap in capacities]))]
            elif self.program.classregmoduleinfo.use_allowable_class_size_ranges:
                capacity_title = "capacity (allowable range)"
                capacity_inputs = [SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(allowable_class_size_ranges__range_max__gte=cap)})
                                                                     for cap in capacities])),
                                   SelectQInput(options=OrderedDict([(str(cap), {'title': str(cap), 'Q': Q(allowable_class_size_ranges__range_min__lte=cap)})
                                                                     for cap in capacities]))]

        status_filter = SearchFilter(
            name='status', title='the status',
            inputs=[SelectInput(field_name='status', options={
                str(k): v for k, v in STATUS_CHOICES})])
        title_filter = SearchFilter(
            name='title', title='title containing',
            inputs=[TextInput(field_name='title__icontains', english_name='')])
        username_filter = SearchFilter(
            name='username', title='teacher username containing',
            inputs=[TextInput(field_name='teachers__username__contains',
                              english_name='')])
        all_scheduled_filter = SearchFilter(
            name="all_scheduled", title="all sections scheduled",
            # Exclude classes with sections with null meeting times
            inverted=True,
            inputs=[ConstantInput(Q(sections__meeting_times__isnull=True))],
        )
        some_scheduled_filter = SearchFilter(
            name="some_scheduled", title="some sections scheduled",
            # Get classes with sections with non-null meeting times
            inputs=[ConstantInput(Q(sections__meeting_times__isnull=False))],
        )

        message_for_directors_filter = SearchFilter(
            name="message_for_directors", title="a message to the directors",
            # Get classes with a message to the directors
            inverted=True,
            inputs=[ConstantInput(Q(message_for_directors=""))],
        )

        purchase_request_filter = SearchFilter(
            name="purchase_request", title="a purchase request",
            # Get classes with a purchase request
            inverted=True,
            inputs=[ConstantInput(Q(purchase_requests__isnull=True) | Q(purchase_requests=""))],
        )

        room_request_filter = SearchFilter(
            name="room_request", title="a room request",
            # Get classes with a room request
            inverted=True,
            inputs=[ConstantInput(Q(requested_room__isnull=True) | Q(requested_room=""))],
        )

        prereq_filter = SearchFilter(
            name="prereqs", title="prerequisites",
            # Get classes with specified prerequisites
            inverted=True,
            inputs=[ConstantInput(Q(prereqs__isnull=True) | Q(prereqs=""))],
        )

        hardness_choices = TeacherClassRegForm.hardness_choices
        if Tag.getTag('teacherreg_difficulty_choices'):
            hardness_choices = json.loads(Tag.getTag('teacherreg_difficulty_choices'))
        hardness_filter = SearchFilter(
            name='hardness_rating', title='the hardness rating',
            inputs=[SelectInput(field_name='hardness_rating',
                                options=OrderedDict([(hardness[0], hardness[1]) for hardness in hardness_choices]))])

        filters = [
                status_filter,
                category_filter,
                duration_filter,
                sections_filter,
                grade_filter,
                title_filter,
                username_filter,
                message_for_directors_filter,
                purchase_request_filter,
                room_request_filter,
                prereq_filter,
                hardness_filter,
                flag_filter,
                any_flag_filter,
                resource_filter,
                any_resource_filter,
                all_scheduled_filter,
                some_scheduled_filter,
            ]

        if capacity_inputs:
            capacity_filter = SearchFilter(
                name='capacity', title= capacity_title + ' between X and Y',
                inputs=capacity_inputs)
            filters.append(capacity_filter)

        if Tag.getTag('class_style_choices'):
            style_choices = json.loads(Tag.getTag('class_style_choices'))
            style_filter = SearchFilter(
                name='class_style', title='the class style',
                inputs=[SelectInput(field_name='class_style',
                                    options={style[0]: style[1] for style in style_choices})])
            filters.append(style_filter)

        return QueryBuilder(
            base=ClassSubject.objects.filter(parent_program=self.program),
            english_name="classes",
            filters=filters)

    @main_call
    @needs_admin
    def classsearch(self, request, tl, one, two, module, extra, prog):
        data = request.GET.get('query')
        query_builder = self.query_builder()
        context = {
            'query_builder': query_builder,
            'program': self.program,
            'query': None,
        }
        namequery = request.GET.get('namequery')
        decoded = None
        if data is not None:
            decoded = json.loads(data)
        elif namequery: # only search if not None and not ""
            # if this looks like a class ID then just go to its manage page
            id_match = re.match('^[a-zA-Z]?(\\d+)$', namequery)
            if id_match:
                id_query = int(id_match.group(1))
                try:
                    subj = ClassSubject.objects.get(id=id_query)
                    return HttpResponseRedirect(subj.get_absolute_url())
                except ClassSubject.DoesNotExist:
                    context['failed_id_search'] = True
                    context['id_query'] = id_query
            decoded = {'filter': 'title', 'negated': False, 'values': [namequery]}

        if decoded is not None:
            queryset = query_builder.as_queryset(decoded)
            queryset = queryset.distinct().order_by('id').prefetch_related(
                'flags', 'flags__flag_type', 'teachers', 'category',
                'sections', 'sections__resourcerequest_set')
            if request.GET.get('randomize'):
                queryset = list(queryset)
                random.shuffle(queryset)
            if request.GET.get('lucky'):
                if queryset:
                    return HttpResponseRedirect(queryset[0].get_absolute_url())
                # if you're not lucky enough and no classes satisfying your
                # search exist, fall through and send you to the class search
                # page as usual
            context['query'] = decoded
            context['queryset'] = queryset
            context['IDs'] = [cls.id for cls in queryset]
            context['flag_types'] = self.program.flag_types.all()
            context['regtypes'] = sorted(RegistrationType.objects.all(), key=lambda a: str(a))
        return render_to_response(self.baseDir()+'class_search.html',
                                  request, context)

    def isStep(self):
        return False
