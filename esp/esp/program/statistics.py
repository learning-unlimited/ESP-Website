
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
import json
from collections import Counter, OrderedDict, defaultdict

from django.db.models import Count, Sum, F, DecimalField, Min, Max, Q
from django.template.loader import render_to_string

from esp.accounting.models import FinancialAidGrant
from esp.program.models import (ClassSection, ClassSubject, FinancialAidRequest,
                                StudentRegistration, StudentSubjectInterest)
from esp.cal.models import Event
from esp.program.class_status import ClassStatus
from esp.users.models import ESPUser, Record

"""
This file contains a set of functions used to perform statistics queries
specified using a StatisticsQueryForm (esp/program/forms.py).
The /manage/statistics view function (statistics in esp/program/views.py)
will try to call one or more of these functions based on the query specified
in the form.

Do not place a top-level function in this file if you would not like it to
be supported as a type of query, unless its name starts with an underscore
(private helpers are never dispatched as queries).
"""

def zipcodes(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   Get zip codes and filter out invalid ones
    zip_dict = {}
    result_dict['invalid'] = 0
    for profile in profiles:
        if profile.contact_user:
            zip_code = profile.contact_user.address_zip
            if zip_code and len(zip_code) == 5 and zip_code.isnumeric():
                if zip_code not in zip_dict:
                    zip_dict[zip_code] = 0
                zip_dict[zip_code] += 1
            else:
                result_dict['invalid'] += 1
        else:
            result_dict['invalid'] += 1
    zip_codes = sorted(zip_dict.keys())
    zip_counts = [zip_dict[x] for x in zip_codes]

    #   Compile and render
    result_dict['zip_data'] = sorted(zip(zip_codes, zip_counts), key=lambda pair: -pair[1])
    if form.cleaned_data['limit']:
        result_dict['zip_data'] = result_dict['zip_data'][:form.cleaned_data['limit']]
    return render_to_string('program/statistics/zip_codes.html', result_dict)

def demographics(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   Get aggregate 'vitals' info via cross-program SQL aggregation.
    agg = (
        ClassSection.objects
        .filter(
            parent_class__parent_program__in=programs,
            status=ClassStatus.ACCEPTED,
        )
        .aggregate(
            num_classes=Count('parent_class', distinct=True),
            num_sections=Count('id'),
            num_class_hours=Sum('duration'),
            num_student_class_hours=Sum(
                F('duration') * F('parent_class__class_size_max'),
                output_field=DecimalField(),
            ),
        )
    )
    result_dict['num_classes'] = agg['num_classes'] or 0
    result_dict['num_sections'] = agg['num_sections'] or 0
    result_dict['num_class_hours'] = int(agg['num_class_hours'] or 0)
    result_dict['num_student_class_hours'] = int(agg['num_student_class_hours'] or 0)

    #   Get grade/age info
    gradyear_dict = {}
    birthyear_dict = {}
    for profile in profiles:
        if profile.student_info:
            grad_year = profile.student_info.graduation_year
            if grad_year is not None:
                if grad_year not in gradyear_dict:
                    gradyear_dict[grad_year] = 0
                gradyear_dict[grad_year] += 1

            if profile.student_info.dob:
                birth_year = profile.student_info.dob.year
                if birth_year not in birthyear_dict:
                    birthyear_dict[birth_year] = 0
                birthyear_dict[birth_year] += 1

    #   Get financial aid info using bulk queries instead of per-student loops.

    #   1. All students who applied (have a done=True financial aid request)
    #   2. Of those, students with reduced_lunch=True
    applied_user_ids = set()
    lunch_user_ids = set()
    for user_id, reduced_lunch in FinancialAidRequest.objects.filter(
        user__in=students,
        program__in=programs,
        done=True,
    ).values_list('user_id', 'reduced_lunch'):
        applied_user_ids.add(user_id)
        if reduced_lunch:
            lunch_user_ids.add(user_id)

    #   3. Students who have been approved (have a FinancialAidGrant)
    approved_user_ids = set(
        FinancialAidGrant.objects.filter(
            request__user__in=students,
            request__program__in=programs,
        ).values_list('request__user_id', flat=True)
    )

    #   Compile and render
    grad_years = sorted(gradyear_dict.keys())
    grad_counts = [gradyear_dict[key] for key in grad_years]
    result_dict['gradyear_data'] = list(zip(grad_years, grad_counts))
    birth_years = sorted(birthyear_dict.keys())
    birth_counts = [birthyear_dict[key] for key in birth_years]
    result_dict['birthyear_data'] = list(zip(birth_years, birth_counts))
    result_dict['finaid_applied'] = len(applied_user_ids)
    result_dict['finaid_lunch'] = len(lunch_user_ids)
    result_dict['finaid_approved'] = len(applied_user_ids & approved_user_ids)
    return render_to_string('program/statistics/demographics.html', result_dict)

def schools(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   Count by name of every student's school
    school_dict = {}
    result_dict['num_k12school'] = 0
    result_dict['num_school'] = 0
    for profile in profiles:
        if profile.student_info:
            if profile.student_info.k12school:
                if profile.student_info.k12school.name not in school_dict:
                    school_dict[profile.student_info.k12school.name] = 0
                school_dict[profile.student_info.k12school.name] += 1
                result_dict['num_k12school'] += 1
            elif profile.student_info.school:
                if profile.student_info.school not in school_dict:
                    school_dict[profile.student_info.school] = 0
                school_dict[profile.student_info.school] += 1
                result_dict['num_school'] += 1

    #   Compile and render
    schools = sorted(school_dict.keys())
    school_counts = [school_dict[school] for school in schools]
    result_dict['school_data'] = sorted(zip(schools, school_counts), key=lambda pair: -pair[1])
    if form.cleaned_data['limit']:
        result_dict['school_data'] = result_dict['school_data'][:form.cleaned_data['limit']]
    return render_to_string('program/statistics/schools.html', result_dict)

def startreg(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   Get first class registration bit and confirmation bit for each student and bin by day.
    #   Uses two bulk queries instead of per-student per-program loops.
    program_lookup = {p.id: p for p in programs}
    reg_dict = {program: defaultdict(int) for program in programs}
    confirm_dict = {program: defaultdict(int) for program in programs}

    #   Bulk-fetch the earliest registration date per (student, program)
    first_regs = (
        StudentRegistration.objects.filter(
            user__in=students,
            section__parent_class__parent_program__in=programs,
        )
        .values('user_id', 'section__parent_class__parent_program')
        .annotate(first_date=Min('start_date'))
    )
    for entry in first_regs:
        prog = program_lookup.get(entry['section__parent_class__parent_program'])
        if prog and entry['first_date']:
            reg_dict[prog][entry['first_date'].date()] += 1

    #   Bulk-fetch the latest confirmation time per (student, program)
    last_confirms = (
        Record.objects.filter(
            user__in=students,
            event__name='reg_confirmed',
            program__in=programs,
        )
        .values('user_id', 'program_id')
        .annotate(last_time=Max('time'))
    )
    for entry in last_confirms:
        prog = program_lookup.get(entry['program_id'])
        if prog and entry['last_time']:
            confirm_dict[prog][entry['last_time'].date()] += 1

    #   Compile and render
    startreg_list = []
    confirm_list = []
    for program in programs:
        reg_dates = sorted(reg_dict[program].keys())
        reg_counts = [reg_dict[program][key] for key in reg_dates]
        startreg_list.append(list(zip(reg_dates, reg_counts)))
        confirm_dates = sorted(confirm_dict[program].keys())
        confirm_counts = [confirm_dict[program][key] for key in confirm_dates]
        confirm_list.append(list(zip(confirm_dates, confirm_counts)))
    result_dict['program_data'] = list(zip(programs, startreg_list, confirm_list))

    return render_to_string('program/statistics/startreg.html', result_dict)

def repeats(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   For each student, find out what other programs they registered for and bin by quantity in each program type.
    #   Uses a single bulk query instead of per-student loops.

    #   Fetch all confirmed (user_id, program_url) pairs in one query,
    #   then derive program_type from the url below
    confirmed_pairs = (
        Record.objects.filter(
            user__in=students,
            event__name='reg_confirmed',
        )
        .values_list('user_id', 'program__url')
    )

    #   Group by user: count how many programs of each type they confirmed
    user_type_counts = defaultdict(Counter)
    for user_id, program_url in confirmed_pairs:
        program_type = program_url.split('/')[0] if program_url else program_url
        user_type_counts[user_id][program_type] += 1

    #   Bin students by their (program_type, count) signature
    repeat_count = {}
    for user_id, indiv_count in user_type_counts.items():
        program_types = sorted(indiv_count.keys())
        id_pair = tuple([(pt, indiv_count[pt]) for pt in program_types])
        if id_pair not in repeat_count:
            repeat_count[id_pair] = 0
        repeat_count[id_pair] += 1

    #   Compile and render
    key_map = {}
    repeat_labels = []
    for key in repeat_count:
        if len(key) > 0:
            repeat_labels.append(', '.join(['%dx %s' % (x[1], x[0]) for x in key]))
            key_map[repeat_labels[-1]] = key
    repeat_labels.sort()
    repeat_counts = []
    for label in repeat_labels:
        repeat_counts.append(repeat_count[key_map[label]])
    result_dict['repeat_data'] = list(zip(repeat_labels, repeat_counts))
    return render_to_string('program/statistics/repeats.html', result_dict)

def heardabout(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   Group most popular reasons for hearing about the program
    reasons_dict = {}
    case_map = {}
    for profile in profiles:
        if profile.student_info:
            #   Attempt to maintain some semblance of similarity by removing punctuation
            ha_str = profile.student_info.heard_about
            if ha_str:
                ha_key = ha_str.rstrip('s').lower()
                for char in ' _:-/.,!?+':
                    ha_key = ha_key.replace(char, '')
                if ha_key not in case_map:
                    case_map[ha_key] = ha_str
                    reasons_dict[ha_str] = 0
                reasons_dict[case_map[ha_key]] += 1

    #   Compile and render
    reasons = list(reasons_dict.keys())
    counts = [reasons_dict[x] for x in reasons]
    result_dict['heardabout_data'] = sorted(zip(reasons, counts), key=lambda pair: -pair[1])
    if form.cleaned_data['limit']:
        result_dict['heardabout_data'] = result_dict['heardabout_data'][:form.cleaned_data['limit']]
    return render_to_string('program/statistics/heardabout.html', result_dict)

def hours(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}

    #   Bin students by registered timeslots per program.
    #   Uses bulk queries across all programs instead of per-program, per-student loops.
    enrolled_list = []
    attended_list = []
    students_list = []
    timeslots_enrolled_list = []
    timeslots_attended_list = []

    def timeslots_by_program_and_user(registrations):
        #   Group (program_id, user_id, timeslot_id) triples into {program_id: {user_id: {timeslot_ids}}}
        result = defaultdict(lambda: defaultdict(set))
        for program_id, user_id, timeslot_id in (
            registrations
            .filter(user__in=students, section__parent_class__parent_program__in=programs)
            .values_list('section__parent_class__parent_program_id', 'user_id', 'section__meeting_times')
            .distinct()
        ):
            if timeslot_id is not None:
                result[program_id][user_id].add(timeslot_id)
        return result

    #   Bulk-fetch timeslots for enrolled students
    enrolled_timeslots = timeslots_by_program_and_user(
        StudentRegistration.valid_objects().filter(relationship__name='Enrolled'))
    #   Bulk-fetch timeslots for attended students
    attended_timeslots = timeslots_by_program_and_user(
        StudentRegistration.objects.filter(relationship__name='Attended'))

    #   We also need actual Event objects for timeslots_enrolled/attended dicts.
    #   Fetch all relevant timeslot events in one query.
    all_timeslot_ids = set()
    for by_user in list(enrolled_timeslots.values()) + list(attended_timeslots.values()):
        for ts_set in by_user.values():
            all_timeslot_ids |= ts_set
    timeslot_lookup = {e.id: e for e in Event.objects.filter(id__in=all_timeslot_ids)}

    for program in programs:
        #   Build the same dicts as the original code (students with no timeslots are not counted)
        enrolled_dict = defaultdict(int)
        attended_dict = defaultdict(int)
        timeslots_enrolled_dict = defaultdict(int)
        timeslots_attended_dict = defaultdict(int)

        for enrolled_ts in enrolled_timeslots[program.id].values():
            enrolled_dict[len(enrolled_ts)] += 1
            for ts_id in enrolled_ts:
                ts = timeslot_lookup.get(ts_id)
                if ts:
                    timeslots_enrolled_dict[ts] += 1

        for attended_ts in attended_timeslots[program.id].values():
            attended_dict[len(attended_ts)] += 1
            for ts_id in attended_ts:
                ts = timeslot_lookup.get(ts_id)
                if ts:
                    timeslots_attended_dict[ts] += 1

        timeslots_enrolled_list.append(dict(timeslots_enrolled_dict))
        timeslots_attended_list.append(dict(timeslots_attended_dict))
        enrolled_list.append(dict(enrolled_dict))
        attended_list.append(dict(attended_dict))
        students_list.append(len(enrolled_timeslots[program.id]))

    #   Compile and render
    enrolled_flat = []
    attended_flat = []
    timeslots_enrolled_flat = []
    timeslots_attended_flat = []
    for enrolled_dict in enrolled_list:
        hours = sorted(enrolled_dict.keys())
        if 0 in hours:
            hours.remove(0)
        counts = [enrolled_dict[key] for key in hours]
        enrolled_flat.append(list(zip(hours, counts)))
    for attended_dict in attended_list:
        hours = sorted(attended_dict.keys())
        if 0 in hours:
            hours.remove(0)
        counts = [attended_dict[key] for key in hours]
        attended_flat.append(list(zip(hours, counts)))
    for timeslots_dict in timeslots_enrolled_list:
        slots = sorted(timeslots_dict.keys())
        counts = [timeslots_dict[key] for key in slots]
        timeslots_enrolled_flat.append(list(zip(slots, counts)))
    for timeslots_dict in timeslots_attended_list:
        slots = sorted(timeslots_dict.keys())
        counts = [timeslots_dict[key] for key in slots]
        timeslots_attended_flat.append(list(zip(slots, counts)))
    #   Class timeslots for all programs in one query (same filter and order as Program.getTimeSlots())
    timeslots_by_program = defaultdict(list)
    for ts in (Event.objects.filter(program__in=programs, event_type__description='Class Time Block')
               .select_related('event_type').order_by('start')):
        timeslots_by_program[ts.program_id].append(ts)
    program_timeslots = [timeslots_by_program[prog.id] for prog in programs]
    result_dict['hours_data'] = list(zip(programs, enrolled_flat, attended_flat, program_timeslots, timeslots_enrolled_flat, timeslots_attended_flat, students_list))
    return render_to_string('program/statistics/hours.html', result_dict)

def student_reg(form, programs, students, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}
    stat_names = [
        'Student Lottery',
        'Class Lottery',
        'Enrolled',
        'Checked In',
    ]
    prog_stats = []
    # ordered dictionary so the legend is in order
    series_data = OrderedDict((stat, []) for stat in stat_names)
    # Bulk-fetch (program_id, user_id) pairs for each stat across all programs,
    # one query per stat (two for class lottery), instead of several queries
    # per program inside the loop. Uses the same criteria as BigBoardModule.
    def users_by_program(pairs):
        result = defaultdict(set)
        for program_id, user_id in pairs.distinct():
            result[program_id].add(user_id)
        return result
    phasezero_by_program = users_by_program(
        ESPUser.objects
        .filter(phasezerorecord__program__in=programs, id__in=students)
        .values_list('phasezerorecord__program_id', 'id')
    )
    lottery_by_program = users_by_program(
        StudentSubjectInterest.valid_objects()
        .filter(subject__parent_program__in=programs, user__in=students)
        .values_list('subject__parent_program_id', 'user_id')
    )
    for program_id, user_ids in users_by_program(
        StudentRegistration.valid_objects()
        .filter(Q(relationship__name='Interested') | Q(relationship__name__contains='Priority/'),
                section__parent_class__parent_program__in=programs, user__in=students)
        .values_list('section__parent_class__parent_program_id', 'user_id')
    ).items():
        lottery_by_program[program_id] |= user_ids
    enrolled_by_program = users_by_program(
        StudentRegistration.valid_objects()
        .filter(relationship__name='Enrolled',
                section__parent_class__parent_program__in=programs, user__in=students)
        .values_list('section__parent_class__parent_program_id', 'user_id')
    )
    checked_in_by_program = users_by_program(
        Record.objects
        .filter(event__name='attended', program__in=programs, user__in=students)
        .values_list('program_id', 'user_id')
    )
    for program in programs:
        stats_list = []
        # entered student lottery
        stud_lott_num = len(phasezero_by_program[program.id])
        series_data['Student Lottery'].append([program.name, stud_lott_num])
        stats_list.append(stud_lott_num)
        # set class lottery preferences
        class_lott_num = len(lottery_by_program[program.id])
        series_data['Class Lottery'].append([program.name, class_lott_num])
        stats_list.append(class_lott_num)
        # enrolled in at least one class
        enroll_num = len(enrolled_by_program[program.id])
        series_data['Enrolled'].append([program.name, enroll_num])
        stats_list.append(enroll_num)
        # students checked in
        checked_num = len(checked_in_by_program[program.id])
        series_data['Checked In'].append([program.name, checked_num])
        stats_list.append(checked_num)
        prog_stats.append(stats_list)
    prog_data = list(zip(programs, prog_stats))
    graph_data = [{"description": desc, "data": json.dumps(data)} for desc, data in series_data.items()]
    left_axis_data = [
            {"axis_name": "# Students Registered", "series_data": graph_data},
    ]
    result_dict.update({"prog_data": prog_data,
                        "stat_names": stat_names,
                        "x_axis_categories": json.dumps([program.name for program in programs.order_by('id')]),
                        "left_axis_data": left_axis_data,
                       })
    return render_to_string('program/statistics/student_reg.html', result_dict)

def _class_reg_stats(programs, teachers):
    """ Per-program stats for classes taught by `teachers` (excluding lunch),
        using the same criteria as TeacherBigBoardModule, in a fixed number of
        queries. Returns {program_id: {level: {'classes', 'teachers',
        'student_hours'}}} for levels 'registered', 'approved' and 'scheduled'.
    """
    teacher_ids = set(teachers.values_list('id', flat=True))
    classes = ClassSubject.objects.filter(parent_program__in=programs).exclude(category__is_lunch=True)

    class_teachers = defaultdict(set)
    for class_id, teacher_id in classes.values_list('id', 'teachers'):
        if teacher_id in teacher_ids:
            class_teachers[class_id].add(teacher_id)
    sections_by_class = defaultdict(list)
    for section_id, class_id, status, duration in (
        ClassSection.objects.filter(parent_class__in=classes)
        .values_list('id', 'parent_class_id', 'status', 'duration')
    ):
        sections_by_class[class_id].append((section_id, status, duration or 0))
    scheduled_section_ids = set(
        ClassSection.objects.filter(parent_class__in=classes, meeting_times__isnull=False)
        .values_list('id', flat=True)
    )

    stats = defaultdict(lambda: {level: {'classes': 0, 'teachers': set(), 'student_hours': 0}
                                 for level in ('registered', 'approved', 'scheduled')})
    for class_id, program_id, status, class_size_max in classes.values_list(
            'id', 'parent_program_id', 'status', 'class_size_max'):
        taught_by = class_teachers.get(class_id)
        if not taught_by:
            continue
        sections = sections_by_class[class_id]
        #   Approved: an approved class with at least one approved section
        #   (only approved sections count towards hours); scheduled: of those,
        #   sections with meeting times.
        approved_sections = [sec for sec in sections if sec[1] > 0] if status > 0 else []
        scheduled_sections = [sec for sec in approved_sections if sec[0] in scheduled_section_ids]
        for level, level_sections in (('registered', sections),
                                      ('approved', approved_sections),
                                      ('scheduled', scheduled_sections)):
            if level != 'registered' and not level_sections:
                continue
            level_stats = stats[program_id][level]
            level_stats['classes'] += 1
            level_stats['teachers'] |= taught_by
            level_stats['student_hours'] += sum(sec[2] for sec in level_sections) * (class_size_max or 0)
    return stats

def teacher_reg(form, programs, teachers, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}
    stat_names = [
        'Class Registered',
        'Class Approved',
        'Class Scheduled',
    ]
    prog_stats = []
    # ordered dictionary so the legend is in order
    series_data = OrderedDict((stat, []) for stat in stat_names)
    class_stats = _class_reg_stats(programs, teachers)
    for program in programs:
        stats_list = []
        # teachers that registered a class
        teach_reg = len(class_stats[program.id]['registered']['teachers'])
        series_data['Class Registered'].append([program.name, teach_reg])
        stats_list.append(teach_reg)
        # teachers with an approved class
        teach_app = len(class_stats[program.id]['approved']['teachers'])
        series_data['Class Approved'].append([program.name, teach_app])
        stats_list.append(teach_app)
        # teachers with a scheduled class
        teach_sch = len(class_stats[program.id]['scheduled']['teachers'])
        series_data['Class Scheduled'].append([program.name, teach_sch])
        stats_list.append(teach_sch)
        prog_stats.append(stats_list)
    prog_data = list(zip(programs, prog_stats))
    graph_data = [{"description": desc, "data": json.dumps(data)} for desc, data in series_data.items()]
    left_axis_data = [
        {"axis_name": "# Teachers", "series_data": graph_data},
    ]
    result_dict.update({"prog_data": prog_data,
                        "stat_names": stat_names,
                        "x_axis_categories": json.dumps([program.name for program in programs.order_by('id')]),
                        "left_axis_data": left_axis_data,
                       })
    return render_to_string('program/statistics/teacher_reg.html', result_dict)

def class_reg(form, programs, teachers, profiles, result_dict=None):
    if result_dict is None:
        result_dict = {}
    stat_categories = ["Classes", "Class-student-hours"]
    stat_names = [
        'Classes Registered',
        'Classes Approved',
        'Classes Scheduled',
        'Class-student-hours Registered',
        'Class-student-hours Approved',
        'Class-student-hours Scheduled',
    ]
    prog_stats = []
    # ordered dictionary so the legend is in order
    series_data = OrderedDict((stat, []) for stat in stat_names)
    class_stats = _class_reg_stats(programs, teachers)
    for program in programs:
        stats_list = []
        # registered classes
        class_reg = class_stats[program.id]['registered']['classes']
        series_data['Classes Registered'].append([program.name, class_reg])
        stats_list.append(class_reg)
        # approved classes
        class_app = class_stats[program.id]['approved']['classes']
        series_data['Classes Approved'].append([program.name, class_app])
        stats_list.append(class_app)
        class_sch = class_stats[program.id]['scheduled']['classes']
        series_data['Classes Scheduled'].append([program.name, class_sch])
        stats_list.append(class_sch)
        student_hours = class_stats[program.id]['registered']['student_hours']
        series_data['Class-student-hours Registered'].append([program.name, float(student_hours)])
        stats_list.append(float(student_hours))
        student_hours_approved = class_stats[program.id]['approved']['student_hours']
        series_data['Class-student-hours Approved'].append([program.name, float(student_hours_approved)])
        stats_list.append(float(student_hours_approved))
        student_hours_scheduled = class_stats[program.id]['scheduled']['student_hours']
        series_data['Class-student-hours Scheduled'].append([program.name, float(student_hours_scheduled)])
        stats_list.append(float(student_hours_scheduled))
        prog_stats.append(stats_list)
    prog_data = list(zip(programs, prog_stats))
    graph_data = [{"description": desc, "data": json.dumps(data)} for desc, data in list(series_data.items())[0:3]]
    left_axis_data = [
        {"axis_name": "# Classes", "series_data": graph_data},
    ]
    graph_data = [{"description": desc, "data": json.dumps(data)} for desc, data in list(series_data.items())[3:6]]
    right_axis_data = [
        {"axis_name": "# Class-student-hours", "series_data": graph_data},
    ]
    result_dict.update({"prog_data": prog_data,
                        "stat_categories": stat_categories,
                        "stats_per_category": len(stat_names)//len(stat_categories),
                        "stat_names": [stat_name.split(' ')[1] for stat_name in stat_names],
                        "x_axis_categories": json.dumps([program.name for program in programs.order_by('id')]),
                        "left_axis_data": left_axis_data,
                        "right_axis_data": right_axis_data,
                       })
    return render_to_string('program/statistics/class_reg.html', result_dict)
