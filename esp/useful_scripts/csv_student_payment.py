#!/usr/bin/env python2
#
# Add accounting records for students that have already paid (e.g. on an external website).
# Assumes that a student has paid for the entirety of their amount due.
#
# Requires the name of the program and a csv that has a column named 'username'
# (which contains student usernames or user ids). Any other columns will be ignored.
#

from script_setup import *

from esp.program.models import Program
from esp.users.models import ESPUser
from esp.accounting.models import *
from esp.accounting.controllers import IndividualAccountingController

import csv
import os
import argparse

from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description = "Add accounting records for students that have already paid")
    parser.add_argument("program", help="Program name")
    parser.add_argument("csv_filename",
                        help="Full path to CSV file with student information")
    args = parser.parse_args()

    PROGRAM = Program.objects.get(name=args.program)

    filename = os.path.expanduser(args.csv_filename)
    csvfile = open(filename, "r")
    reader = csv.DictReader(csvfile)

    if 'username' not in reader.fieldnames:
        print "Error: csv file does not have a 'username' column"
    else:
        usernames = [x['username'] for x in reader]
        lineitem = LineItemType.objects.get(text = "Student payment", program = PROGRAM)
        acc = Account.objects.get(name = "receivable")
        for username in usernames:
            try:
                student = ESPUser.objects.get(id=username)
            except:
                try:
                    student = ESPUser.objects.get(username=username)
                except:
                    print "No user with id/username=" + str(username) + " found"
                    continue
            iac = IndividualAccountingController(PROGRAM, student)
            if not iac.transfers_to_program_exist():
                print username + " has no charges for " + PROGRAM.name
            else:
                amt = iac.amount_due()
                if amt <= 0:
                    print username + " has no amount due for " + PROGRAM.name
                else:
                    transfer = Transfer.objects.create(destination = acc, user = student, line_item = lineitem, amount_dec = amt)
                    print username + " has now paid " + str(amt) + " for " + PROGRAM.name

        print "All usernames processed."

if __name__ == '__main__':
    main()
