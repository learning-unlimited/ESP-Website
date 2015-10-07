import json

from django.db.models.query import Q

from esp.program.modules.base import ProgramModuleObj, main_call, needs_admin
from esp.program.models.class_ import ClassSubject, STATUS_CHOICES
from esp.program.models.flags import ClassFlagType
from esp.utils.query_builder import QueryBuilder, SearchFilter
from esp.utils.query_builder import SelectInput, ConstantInput, TextInput
from esp.utils.query_builder import OptionalInput, DatetimeInput
from esp.web.util import render_to_response

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
        }

    class Meta:
        proxy = True

    def query_builder(self):
        flag_types = ClassFlagType.get_flag_types(program=self.program)
        flag_datetime_inputs = [
            OptionalInput(name=t, inner=DatetimeInput(
                field_name='flags__%s_time' % t, english_name=''))
            for t in ['created', 'modified']]
        flag_select_input = SelectInput(
            field_name='flags__flag_type', english_name='type',
            options={str(ft.id): ft.name for ft in flag_types})
        flag_filter = SearchFilter(name='flag', title='the flag',
                                   inputs=[flag_select_input] +
                                   flag_datetime_inputs)
        any_flag_filter = SearchFilter(name='any_flag', title='any flag',
                                       inputs=flag_datetime_inputs)

        categories = list(self.program.class_categories.all())
        if self.program.open_class_registration:
            categories.append(self.program.open_class_category)
        category_filter = SearchFilter(
            name='category', title='the category',
            inputs=[SelectInput(field_name='category', english_name='',
                                options={str(cat.id): cat.category
                                         for cat in categories})])

        status_filter = SearchFilter(
            name='status', title='the status',
            inputs=[SelectInput(field_name='status', english_name='', options={
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
                all_scheduled_filter,
                some_scheduled_filter,
            ])

    @main_call
    @needs_admin
    def classsearch(self, request, tl, one, two, module, extra, prog):
        data = request.GET.get('query')
        query_builder = self.query_builder()
        if data is None:
            # Display a blank query builder
            context = {
                'query_builder': query_builder,
                'program': self.program,
            }
            return render_to_response(self.baseDir()+'query_builder.html',
                                      request, context)
        else:
            decoded = json.loads(data)
            queryset = query_builder.as_queryset(decoded)
            queryset = queryset.distinct().order_by('id').prefetch_related(
                'flags', 'flags__flag_type', 'teachers', 'category',
                'sections', 'sections__resourcerequest_set')
            english = query_builder.as_english(decoded)
            context = {
                'queryset': queryset,
                'english': english,
                'program': self.program,
                'flag_types': self.program.flag_types.all(),
            }
            return render_to_response(self.baseDir()+'search_results.html',
                                      request, context)
