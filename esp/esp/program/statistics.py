
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
from django.template.loader import render_to_string

from esp.program.models import Program, StudentRegistration
from esp.users.models import Record

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
    zip_codes = zip_dict.keys()
    zip_codes.sort()

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
        result_dict['num_classes'] += program.classes().select_related().filter(status=10).count()
        result_dict['num_sections'] += program.sections().select_related().filter(status=10).count()
        for section in program.sections().select_related().filter(status=10):
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
    grad_years = gradyear_dict.keys()
    grad_years.sort()
    grad_counts = [gradyear_dict[key] for key in grad_years]
    result_dict['gradyear_data'] = zip(grad_years, grad_counts)
    birth_years = birthyear_dict.keys()
    birth_years.sort()
    birth_counts = [birthyear_dict[key] for key in birth_years]
    result_dict['birthyear_data'] = zip(birth_years, birth_counts)
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
    schools = school_dict.keys()
    schools.sort()
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

            reg_bits = StudentRegistration.objects.filter(user=student).order_by('start_date')
            if reg_bits.exists():
                if reg_bits[0].start_date.date() not in reg_dict[program]:
                    reg_dict[program][reg_bits[0].start_date.date()] = 0
                reg_dict[program][reg_bits[0].start_date.date()] += 1

            confirm_bits = Record.objects.filter(user=student, event='reg_confirmed', program=program).order_by('-date')
            if confirm_bits.exists():
                if confirm_bits[0].date.date() not in confirm_dict[program]:
                    confirm_dict[program][confirm_bits[0].date.date()] = 0
                confirm_dict[program][confirm_bits[0].date.date()] += 1

    #   Compile and render
    startreg_list = []
    confirm_list = []
    for program in programs:
        reg_dates = reg_dict[program].keys()
        reg_dates.sort()
        reg_counts = [reg_dict[program][key] for key in reg_dates]
        startreg_list.append(zip(reg_dates, reg_counts))
        confirm_dates = confirm_dict[program].keys()
        confirm_dates.sort()
        confirm_counts = [confirm_dict[program][key] for key in confirm_dates]
        confirm_list.append(zip(confirm_dates, confirm_counts))
    result_dict['program_data'] = zip(programs, startreg_list, confirm_list)

    return render_to_string('program/statistics/startreg.html', result_dict)


def repeats(form, programs, students, profiles, result_dict={}):

    #   For each student, find out what other programs they registered for and bin by quantity in each program type
    repeat_count = {}
    for student in students:
        programs = Program.objects.filter(record__user=student, record__event='reg_confirmed')
        indiv_count = {}
        for program in programs:
            if program.program_type not in indiv_count:
                indiv_count[program.program_type] = 0
            indiv_count[program.program_type] += 1
        program_types = indiv_count.keys()
        program_types.sort()
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
    result_dict['repeat_data'] = zip(repeat_labels, repeat_counts)
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
    reasons = reasons_dict.keys()
    counts = [reasons_dict[x] for x in reasons]
    result_dict['heardabout_data'] = sorted(zip(reasons, counts), key=lambda pair: -pair[1])
    if form.cleaned_data['limit']:
        result_dict['heardabout_data'] = result_dict['heardabout_data'][:form.cleaned_data['limit']]
    return render_to_string('program/statistics/heardabout.html', result_dict)

def hours(form, programs, students, profiles, result_dict={}):

    #   Bin students by registered timeslots per program
    stats_list = []
    students_list = []
    timeslots_list = []
    for program in programs:
        prog_students = 0
        stats_dict = {}
        timeslots_dict = {}
        for student in students:
            sections = student.getEnrolledSections(program)
            timeslots = []
            for sec in sections:
                timeslots += sec.meeting_times.all()
            timeslots = set(timeslots)
            if len(timeslots) not in stats_dict:
                stats_dict[len(timeslots)] = 0
            stats_dict[len(timeslots)] += 1
            if len(timeslots) > 0:
                prog_students += 1
            for timeslot in timeslots:
                if timeslot not in timeslots_dict:
                    timeslots_dict[timeslot] = 0
                timeslots_dict[timeslot] += 1
        timeslots_list.append(timeslots_dict)
        stats_list.append(stats_dict)
        students_list.append(prog_students)

    #   Compile and render
    stats_flat = []
    timeslots_flat = []
    for stats_dict in stats_list:
        hours = stats_dict.keys()
        hours.sort(key=lambda x: -x)
        if 0 in hours:
            hours.remove(0)
        counts = [stats_dict[key] for key in hours]
        stats_flat.append(zip(hours, counts))
    for timeslots_dict in timeslots_list:
        slots = timeslots_dict.keys()
        slots.sort()
        counts = [timeslots_dict[key] for key in slots]
        timeslots_flat.append(zip(slots, counts))
    result_dict['hours_data'] = zip(programs, stats_flat, timeslots_flat, students_list)
    return render_to_string('program/statistics/hours.html', result_dict)

