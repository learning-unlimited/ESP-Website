
from __future__ import absolute_import
from __future__ import division
from six.moves import zip
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
from collections import OrderedDict
from numpy import mean

from django.template.loader import render_to_string

from esp.program.models import Program, StudentRegistration
from esp.program.class_status import ClassStatus
from esp.users.models import ESPUser, Record
from esp.program.modules.handlers.bigboardmodule import BigBoardModule
from esp.program.modules.handlers.teacherbigboardmodule import TeacherBigBoardModule

"""
This file contains a set of functions used to perform statistics queries
specified using a StatisticsQueryForm (esp/program/forms.py).
The /manage/statistics view function (statistics in esp/program/views.py)
will try to call one or more of these functions based on the query specified
in the form.

Do not place a top-level function in this file if you would not like it to
be supported as a type of query.
"""

def zipcodes(form, programs, students, profiles, result_dict={}):

    #   Get zip codes
    zip_dict = {}
    for profile in profiles:
        if profile.contact_user:
            if profile.contact_user.address_zip not in zip_dict:
                zip_dict[profile.contact_user.address_zip] = 0
            zip_dict[profile.contact_user.address_zip] += 1
        else:
            if 'N/A' not in zip_dict:
                zip_dict['N/A'] = 0
            zip_dict['N/A'] += 1
    zip_codes = sorted(zip_dict.keys())

    #   Filter out invalid zip codes
    result_dict['invalid'] = 0
    for code in zip_codes:
        if not code or len(code) != 5 or not code.isnumeric():
            result_dict['invalid'] += zip_dict[code]
            del zip_dict[code]
            zip_codes.remove(code)
    zip_counts = [zip_dict[x] for x in zip_codes]

    #   Compile and render
    result_dict['zip_data'] = sorted(zip(zip_codes, zip_counts), key=lambda pair: -pair[1])
    if form.cleaned_data['limit']:
        result_dict['zip_data'] = result_dict['zip_data'][:form.cleaned_data['limit']]
    return render_to_string('program/statistics/zip_codes.html', result_dict)


def demographics(form, programs, students, profiles, result_dict={}):

    #   Get aggregate 'vitals' info
    result_dict['num_classes'] = result_dict['num_sections'] = 0
    result_dict['num_class_hours'] = result_dict['num_student_class_hours'] = 0
    for program in programs:
        result_dict['num_classes'] += program.classes().select_related().filter(status=ClassStatus.ACCEPTED).count()
        result_dict['num_sections'] += program.sections().select_related().filter(status=ClassStatus.ACCEPTED).count()
        for section in program.sections().select_related().filter(status=ClassStatus.ACCEPTED):
            result_dict['num_class_hours'] += section.duration
            result_dict['num_student_class_hours'] += section.duration*section.parent_class.class_size_max
    result_dict['num_class_hours'] = int(result_dict['num_class_hours'])
    result_dict['num_student_class_hours'] = int(result_dict['num_student_class_hours'])

    #   Get grade/age info
    gradyear_dict = {}
    birthyear_dict = {}
    for profile in profiles:
        if profile.student_info:
            if profile.student_info.graduation_year and profile.student_info.graduation_year not in gradyear_dict:
                gradyear_dict[profile.student_info.graduation_year] = 0
            gradyear_dict[profile.student_info.graduation_year] += 1

            if profile.student_info.dob:
                if profile.student_info.dob.year not in birthyear_dict:
                    birthyear_dict[profile.student_info.dob.year] = 0
                birthyear_dict[profile.student_info.dob.year] += 1

    #   Get financial aid info
    finaid_applied = []
    finaid_lunch = []
    finaid_approved = []
    for student in students:
        for program in programs:
            if student.appliedFinancialAid(program):
                finaid_applied.append(student.id)
                if student.financialaidrequest_set.filter(program=program, done=True, reduced_lunch=True).count() > 0:
                    finaid_lunch.append(student.id)
                if student.hasFinancialAid(program):
                    finaid_approved.append(student.id)

    #   Compile and render
    grad_years = sorted(gradyear_dict.keys())
    grad_counts = [gradyear_dict[key] for key in grad_years]
    result_dict['gradyear_data'] = list(zip(grad_years, grad_counts))
    birth_years = sorted(birthyear_dict.keys())
    birth_counts = [birthyear_dict[key] for key in birth_years]
    result_dict['birthyear_data'] = list(zip(birth_years, birth_counts))
    result_dict['finaid_applied'] = len(set(finaid_applied))
    result_dict['finaid_lunch'] = len(set(finaid_lunch))
    result_dict['finaid_approved'] = len(set(finaid_approved))
    return render_to_string('program/statistics/demographics.html', result_dict)


def schools(form, programs, students, profiles, result_dict={}):

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


def startreg(form, programs, students, profiles, result_dict={}):

    #   Get first class registration bit and confirmation bit for each student and bin by day
    reg_dict = {}
    confirm_dict = {}
    for program in programs:
        reg_dict[program] = {}
        confirm_dict[program] = {}

    for student in students:
        for program in programs:

            reg_bits = StudentRegistration.objects.filter(user=student, section__parent_class__parent_program = program).order_by('start_date')
            if reg_bits.exists():
                if reg_bits[0].start_date.date() not in reg_dict[program]:
                    reg_dict[program][reg_bits[0].start_date.date()] = 0
                reg_dict[program][reg_bits[0].start_date.date()] += 1

            confirm_bits = Record.objects.filter(user=student, event__name='reg_confirmed', program=program).order_by('-time')
            if confirm_bits.exists():
                if confirm_bits[0].time.date() not in confirm_dict[program]:
                    confirm_dict[program][confirm_bits[0].time.date()] = 0
                confirm_dict[program][confirm_bits[0].time.date()] += 1

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


def repeats(form, programs, students, profiles, result_dict={}):

    #   For each student, find out what other programs they registered for and bin by quantity in each program type
    repeat_count = {}
    for student in students:
        programs = Program.objects.filter(record__user=student, record__event__name='reg_confirmed')
        indiv_count = {}
        for program in programs:
            if program.program_type not in indiv_count:
                indiv_count[program.program_type] = 0
            indiv_count[program.program_type] += 1
        program_types = sorted(indiv_count.keys())
        id_pair = tuple([tuple([program_type, indiv_count[program_type]]) for program_type in program_types])
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


def heardabout(form, programs, students, profiles, result_dict={}):

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
                    ha_key.replace(char, '')
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

def hours(form, programs, students, profiles, result_dict={}):

    #   Bin students by registered timeslots per program
    enrolled_list = []
    attended_list = []
    students_list = []
    timeslots_enrolled_list = []
    timeslots_attended_list = []
    for program in programs:
        prog_students = 0
        enrolled_dict = {}
        attended_dict = {}
        timeslots_enrolled_dict = {}
        timeslots_attended_dict = {}
        for student in students:
            # calculate number of blocks for which students were enrolled
            sections_enrolled = student.getEnrolledSections(program)
            timeslots = []
            for sec in sections_enrolled:
                timeslots += sec.meeting_times.all()
            timeslots = set(timeslots)
            if len(timeslots) not in enrolled_dict:
                enrolled_dict[len(timeslots)] = 0
            enrolled_dict[len(timeslots)] += 1
            if len(timeslots) > 0:
                prog_students += 1
            for timeslot in timeslots:
                if timeslot not in timeslots_enrolled_dict:
                    timeslots_enrolled_dict[timeslot] = 0
                timeslots_enrolled_dict[timeslot] += 1
            # calculate number of blocks students attended
            # if a student attended two classes during the same block, this will probably double count them
            # but that seems pretty unlikely
            sections_attended = student.getSections(program, ['Attended'], valid_only=False)
            timeslots = []
            for sec in sections_attended:
                timeslots += sec.meeting_times.all()
            timeslots = set(timeslots)
            if len(timeslots) not in attended_dict:
                attended_dict[len(timeslots)] = 0
            attended_dict[len(timeslots)] += 1
            for timeslot in timeslots:
                if timeslot not in timeslots_attended_dict:
                    timeslots_attended_dict[timeslot] = 0
                timeslots_attended_dict[timeslot] += 1
        timeslots_enrolled_list.append(timeslots_enrolled_dict)
        timeslots_attended_list.append(timeslots_attended_dict)
        enrolled_list.append(enrolled_dict)
        attended_list.append(attended_dict)
        students_list.append(prog_students)

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
    program_timeslots = [prog.getTimeSlots() for prog in programs]
    result_dict['hours_data'] = list(zip(programs, enrolled_flat, attended_flat, program_timeslots, timeslots_enrolled_flat, timeslots_attended_flat, students_list))
    return render_to_string('program/statistics/hours.html', result_dict)

def student_reg(form, programs, students, profiles, result_dict={}):
    stat_names = [
        'Student Lottery',
        'Class Lottery',
        'Enrolled',
        'Checked In',
    ]
    prog_stats = []
    # ordered dictionary so the legend is in order
    series_data = OrderedDict((stat, []) for stat in stat_names)
    for program in programs:
        stats_list = []
        # entered student lottery
        stud_lott_num = ESPUser.objects.filter(phasezerorecord__program=program).intersection(students).distinct().count()
        series_data['Student Lottery'].append([program.name, stud_lott_num])
        stats_list.append(stud_lott_num)
        # set class lottery preferences
        class_lott_num = len(BigBoardModule.users_with_lottery(program) & set(students.values_list('id', flat = True)))
        series_data['Class Lottery'].append([program.name, class_lott_num])
        stats_list.append(class_lott_num)
        # enrolled in at least one class
        enroll_num = len(set(BigBoardModule.users_enrolled(program)) & set(students.values_list('id', flat = True)))
        series_data['Enrolled'].append([program.name, enroll_num])
        stats_list.append(enroll_num)
        # students checked in
        checked_num = len(set(BigBoardModule.checked_in_users(program)) & set(students.values_list('id', flat = True)))
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

def teacher_reg(form, programs, teachers, profiles, result_dict={}):
    stat_names = [
        'Class Registered',
        'Class Approved',
        'Class Scheduled',
    ]
    prog_stats = []
    # ordered dictionary so the legend is in order
    series_data = OrderedDict((stat, []) for stat in stat_names)
    for program in programs:
        stats_list = []
        # teachers that registered a class
        teach_reg = TeacherBigBoardModule.num_teachers_teaching(program, teachers = teachers)
        series_data['Class Registered'].append([program.name, teach_reg])
        stats_list.append(teach_reg)
        # teachers with an approved class
        teach_app = TeacherBigBoardModule.num_teachers_teaching(program, approved = True, teachers = teachers)
        series_data['Class Approved'].append([program.name, teach_app])
        stats_list.append(teach_app)
        # teachers with a scheduled class
        teach_sch = TeacherBigBoardModule.num_teachers_teaching(program, approved = True, scheduled = True, teachers = teachers)
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

def class_reg(form, programs, teachers, profiles, result_dict={}):
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
    for program in programs:
        stats_list = []
        # registered classes
        class_reg = TeacherBigBoardModule.num_class_reg(program, teachers = teachers)
        series_data['Classes Registered'].append([program.name, class_reg])
        stats_list.append(class_reg)
        # teachers with an approved class
        class_app = TeacherBigBoardModule.num_class_reg(program, approved = True, teachers = teachers)
        series_data['Classes Approved'].append([program.name, class_app])
        stats_list.append(class_app)
        class_sch = TeacherBigBoardModule.num_class_reg(program, approved = True, scheduled = True, teachers = teachers)
        series_data['Classes Scheduled'].append([program.name, class_sch])
        stats_list.append(class_sch)
        class_hours, student_hours = TeacherBigBoardModule.static_hours(program, teachers = teachers)
        series_data['Class-student-hours Registered'].append([program.name, float(student_hours)])
        stats_list.append(float(student_hours))
        class_hours_approved, student_hours_approved = TeacherBigBoardModule.static_hours(program, approved = True, teachers = teachers)
        series_data['Class-student-hours Approved'].append([program.name, float(student_hours_approved)])
        stats_list.append(float(student_hours_approved))
        class_hours_scheduled, student_hours_scheduled = TeacherBigBoardModule.static_hours(program, approved = True, scheduled = True, teachers = teachers)
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
