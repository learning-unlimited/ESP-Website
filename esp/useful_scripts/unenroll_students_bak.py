#!/usr/bin/env python
"""
Kick students out of their classes (or only next hour's classes, if the
--per-hour option is used) if they haven't checked in yet.
"""

import argparse

from script_setup import *

from esp.program.models import Program, StudentRegistration, RegistrationType
from esp.users.models import ESPUser
from datetime import datetime, timedelta
from django.db.models.aggregates import Min
from esp.dbmail.models import send_mail
import sys, pipes

def do_unenrollment(args):
    enrolled = RegistrationType.objects.get(name='Enrolled')

    prog = Program.objects.get(name=args.program_name)
    relevant_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10).exclude(parent_class__category__category='Lunch')
    # classes that started more than 60 minutes ago
    passed_sections = relevant_sections.filter(begin_time__lt=datetime.now() - timedelta(minutes=60))
    # students who are enrolled in a class that started more than 60 minutes ago, who have not checked in
    students = ESPUser.objects.filter(studentregistration__in=StudentRegistration.valid_objects(), studentregistration__relationship=enrolled, studentregistration__section__in=passed_sections).distinct().exclude(record__program=prog, record__event='attended')
    # classes that start in the next 60 minutes
    upcoming_sections = relevant_sections.filter(begin_time__gt=datetime.now())
    if args.per_hour:
        upcoming_sections = upcoming_sections.filter(begin_time__lt=datetime.now() + timedelta(minutes=60))

    # registrations of missing students for upcoming classes
    registrations = StudentRegistration.valid_objects().filter(user__in=students, section__in=upcoming_sections, relationship=enrolled)
    print("Candidate Registrations to Delete:", len(registrations))

    for i in registrations:
        print("{} {}".format(i.id, i))
    if args.skip_confirm:
        cmd_str = 'y'
    else:
        cmd_str = input("Would you like to delete these registrations [y/N]? --> ")

    if cmd_str.strip().lower() == 'y':
        registrations.update(end_date=datetime.now())
        print('Expired:', registrations)
        return  registrations
    else:
        print('Action cancelled.')
        return  None

def main():
    parser = argparse.ArgumentParser(description='Unenroll missing students from classes.')
    parser.add_argument('program_name', type=str, help='name of the current program')
    parser.add_argument('--per-hour', dest='per_hour', action='store_true', help='Include this argument to clear registrations only for classes starting in the next 60 minutes.')
    parser.add_argument('--skip-confirm', dest='skip_confirm', action='store_true', help='Skip y/n prompt, and instead approve the changes')

    args = parser.parse_args()

    run_cmd = "COMMAND: "+' '.join(pipes.quote(arg) for arg in sys.argv)

    email_subj = "ESP Auto-Unenrollment Script"
    email_from = "server@esp.mit.edu"
    email_to = ["esp-webmasters@mit.edu"]
    try:
        email_msg = run_cmd +"\n\n"
        regs = do_unenrollment(args)
        if regs is None:
            email_msg += "Unenrollment was canceled; no change occurred."
        else:
            if regs:
                email_msg += "Unenrollments processed:"
                for i in regs:
                    email_msg += "\n{} - {}".format(i.id, i)
            else:
                email_msg += "No unenrollments to process."

    except Error as e:
        email_msg = run_cmd +"\n\n"
        email_msg += "Script encountered an error:\n"+e

    send_mail(email_subj, email_msg, email_from, email_to)


if __name__=="__main__":
    main()
