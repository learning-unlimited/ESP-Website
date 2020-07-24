import json
import random
import re

from django.http import HttpResponseRedirect
from django.db.models.query import Q

from esp.program.modules.base import ProgramModuleObj, main_call, needs_admin
from esp.program.models import RegistrationType
from esp.program.models.class_ import ClassSubject, STATUS_CHOICES
from esp.program.models.flags import ClassFlagType
from esp.resources.models import Resource, ResourceType, ResourceRequest
from esp.utils.query_builder import QueryBuilder, SearchFilter
from esp.utils.query_builder import SelectInput, ConstantInput, TextInput
from esp.utils.query_builder import OptionalInput, DatetimeInput
from esp.utils.web import render_to_response

# TODO: this won't work right without class flags enabled


class ClassSearchModule(ProgramModuleObj):
    """Search for classes matching certain criteria."""
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

        return QueryBuilder(
            base=ClassSubject.objects.filter(parent_program=self.program),
            english_name="classes",
            filters=[
                status_filter,
                category_filter,
                title_filter,
                username_filter,
                flag_filter,
                any_flag_filter,
                resource_filter,
                any_resource_filter,
                all_scheduled_filter,
                some_scheduled_filter,
            ])

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
