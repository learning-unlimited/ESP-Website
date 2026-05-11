import json
from django.http import HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string
from django import forms
from esp.utils.web import render_to_response
from esp.program.models import Program, RegistrationProfile
from esp.program.forms import StatisticsQueryForm
from esp.users.models import ESPUser, ZipCode, admin_required

@admin_required
def statistics(request, program=None):

    def get_field_ids(form):
        field_ids = []
        #   Hack to make sure radio buttons are re-parsed correctly by Dojo
        for field_name in form.fields:
            if isinstance(form.fields[field_name].widget, forms.RadioSelect):
                for i in range(len(form.fields[field_name].choices)):
                    field_ids.append('%s_%d' % (field_name, i))
            else:
                field_ids.append(field_name)
        return field_ids

    if request.method == 'POST':
        #   Hack for proper behavior when multiselect fields are hidden
        #   (they contain '' instead of simply being absent like they should)
        post_data = request.POST.copy()
        multiselect_fields = StatisticsQueryForm.get_multiselect_fields()
        for field_name in multiselect_fields:
            if field_name in post_data and post_data[field_name] == '':
                del post_data[field_name]

        form = StatisticsQueryForm(post_data, program=program)

        #   Handle case where all we want is a new form
        if 'update_form' in request.GET:
            form.hide_unwanted_fields()

            #   Return result
            context = {'form': form}
            context['clear_first'] = True
            context['field_ids'] = get_field_ids(form)
            result = {}
            result['statistics_form_contents_html'] = render_to_string('program/statistics/form.html', context)
            result['script'] = render_to_string('program/statistics/script.js', context)
            return HttpResponse(json.dumps(result), content_type='application/json')

        if form.is_valid():
            #   A dictionary for template rendering the results of this query
            result_dict = {}
            #   A dictionary for template rendering the final response
            context = {}

            #   Get list of programs the query applies to
            programs = Program.objects.all()
            if not form.cleaned_data['program_type_all']:
                programs = programs.filter(url__startswith=form.cleaned_data['program_type'])
            if not form.cleaned_data['program_instance_all']:
                programs = programs.filter(url__in=form.cleaned_data['program_instances'])
            result_dict['programs'] = programs

            #   Which registration dimension applies matches StatisticsQueryForm.hide_unwanted_fields:
            #   teacher_reg / class_reg hide student fields; all other stats hide teacher fields.
            #   Hidden fields still leave initial=True on the other role (e.g. teacher_reg_type_all),
            #   which used to OR in teachers_union() for zipcodes etc. and produced enormous SQL.
            stats_query = form.cleaned_data['query']
            teacher_only = stats_query in ('teacher_reg', 'class_reg')

            #   Get list of users the query applies to.
            #   Accumulate per-program registration Q objects, then apply each role
            #   filter once (Student / Teacher). Doing (prog_q & role) for every
            #   program duplicates the groups join on each OR branch and is very
            #   slow; (prog_q1 | prog_q2 | ...) & role is equivalent for students
            #   and avoids that.
            student_reg_types_on_form = [
                choice[0] for choice in form.fields.get('student_reg_types').choices
            ] if 'student_reg_types' in form.fields else []
            teacher_reg_types_on_form = [
                choice[0] for choice in form.fields.get('teacher_reg_types').choices
            ] if 'teacher_reg_types' in form.fields else []
            student_users_q = None
            teacher_users_q = None

            for program in programs:
                student_q = None
                if not teacher_only:
                    if form.cleaned_data.get('student_reg_type_all'):
                        # "All" should be limited to the registration types shown
                        # on the statistics form. `program.students_union()`
                        # includes extra categories like attended_past/enrolled_past
                        # which can be very expensive and are not part of this query.
                        students_objects = program.students(QObjects=True)
                        student_q = Q(pk__in=[])
                        for reg_type in student_reg_types_on_form:
                            if reg_type in students_objects:
                                student_q |= students_objects[reg_type]
                    elif form.cleaned_data.get('student_reg_types'):
                        students_objects = program.students(QObjects=True)
                        student_q = Q(pk__in=[])
                        for reg_type in form.cleaned_data['student_reg_types']:
                            if reg_type in students_objects:
                                student_q |= students_objects[reg_type]

                    if student_q:
                        if student_users_q is None:
                            student_users_q = student_q
                        else:
                            student_users_q |= student_q

                teacher_q = None
                if teacher_only:
                    if form.cleaned_data.get('teacher_reg_type_all'):
                        # Same restriction as the student side.
                        teachers_objects = program.teachers(QObjects=True)
                        teacher_q = Q(pk__in=[])
                        for reg_type in teacher_reg_types_on_form:
                            if reg_type in teachers_objects:
                                teacher_q |= teachers_objects[reg_type]
                    elif form.cleaned_data.get('teacher_reg_types'):
                        teachers_objects = program.teachers(QObjects=True)
                        teacher_q = Q(pk__in=[])
                        for reg_type in form.cleaned_data['teacher_reg_types']:
                            if reg_type in teachers_objects:
                                teacher_q |= teachers_objects[reg_type]

                    if teacher_q:
                        if teacher_users_q is None:
                            teacher_users_q = teacher_q
                        else:
                            teacher_users_q |= teacher_q

            users_q = None
            if student_users_q is not None:
                # Restrict to students so teachers/volunteers with registration-like
                # records are not counted as students.
                users_q = student_users_q & ESPUser.getAllOfType('Student')
            if teacher_users_q is not None:
                tq = teacher_users_q & ESPUser.getAllOfType('Teacher')
                users_q = tq if users_q is None else (users_q | tq)

            if users_q is None:
                users_q = Q(pk__in=[])

            #   Narrow down by school (perhaps not ideal results, but faster)
            if form.cleaned_data['school_query_type'] == 'name':
                users_q = users_q & (Q(studentinfo__school__icontains=form.cleaned_data['school_name']) | Q(studentinfo__k12school__name__icontains=form.cleaned_data['school_name']))
            elif form.cleaned_data['school_query_type'] == 'list':
                k12school_ids = []
                school_names = []
                for item in form.cleaned_data['school_multisel']:
                    if item.startswith('K12:'):
                        k12school_ids.append(int(item[4:]))
                    elif item.startswith('Sch:'):
                        school_names.append(item[4:])
                users_q = users_q & (Q(studentinfo__school__in=school_names) | Q(studentinfo__k12school__id__in=k12school_ids))

            #   Narrow down by Zip code, simply using the latest profile
            #   Note: it would be harder to track users better (i.e. zip code A in fall 2008, zip code B in fall 2009)
            if form.cleaned_data['zip_query_type'] == 'exact':
                users_q = users_q & Q(registrationprofile__contact_user__address_zip=form.cleaned_data['zip_code'], registrationprofile__most_recent_profile=True)
            elif form.cleaned_data['zip_query_type'] == 'partial':
                users_q = users_q & Q(registrationprofile__contact_user__address_zip__startswith=form.cleaned_data['zip_code_partial'], registrationprofile__most_recent_profile=True)
            elif form.cleaned_data['zip_query_type'] == 'distance':
                zipc = ZipCode.objects.get(zip_code=form.cleaned_data['zip_code'])
                zipcodes = zipc.close_zipcodes(form.cleaned_data['zip_code_distance'])
                users_q = users_q & Q(registrationprofile__contact_user__address_zip__in = zipcodes, registrationprofile__most_recent_profile=True)

            #   Distinct PKs only (avoids running the heavy filter twice for count() + list()).
            user_ids = list(
                ESPUser.objects.filter(users_q).values_list('pk', flat=True).distinct()
            )
            result_dict['num_users'] = len(user_ids)
            users = ESPUser.objects.filter(pk__in=user_ids)
            user_list = list(users)
            # Batch-fetch latest profile per user to avoid N+1
            profile_by_user = {}
            if user_list:
                for p in RegistrationProfile.objects.filter(user__in=users).select_related('user').order_by('user_id', '-last_ts'):
                    if p.user_id not in profile_by_user:
                        profile_by_user[p.user_id] = p
            profiles = [profile_by_user.get(u.id) or RegistrationProfile(user=u) for u in user_list]

            #   Accumulate desired information for selected query
            from esp.program import statistics as statistics_functions
            if hasattr(statistics_functions, form.cleaned_data['query']):
                context['result'] = getattr(statistics_functions, form.cleaned_data['query'])(form, programs, users, profiles, result_dict)
            else:
                context['result'] = 'Unsupported query'

            #   Generate response
            form.hide_unwanted_fields()
            context['form'] = form
            context['clear_first'] = False
            context['field_ids'] = get_field_ids(form)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                result = {}
                result['result_html'] = context['result']
                result['script'] = render_to_string('program/statistics/script.js', context)
                return HttpResponse(json.dumps(result), content_type='application/json')
            else:
                return render_to_response('program/statistics.html', request, context)
        else:
            #   Form was submitted but there are problems with it
            form.hide_unwanted_fields()
            context = {'form': form}
            context['clear_first'] = False
            context['field_ids'] = get_field_ids(form)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse(json.dumps({}), content_type='application/json')
            else:
                return render_to_response('program/statistics.html', request, context)

    #   First request, form not yet submitted
    form = StatisticsQueryForm(program=program)
    form.hide_unwanted_fields()
    context = {'form': form}
    context['clear_first'] = False
    context['field_ids'] = get_field_ids(form)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponse(json.dumps(context), content_type='application/json')
    else:
        return render_to_response('program/statistics.html', request, context)
