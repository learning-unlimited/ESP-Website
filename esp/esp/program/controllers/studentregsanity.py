from io import open
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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

from datetime import date, datetime
import logging
logger = logging.getLogger(__name__)

from esp.cal.models import Event
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import StudentRegistration, RegistrationType, RegistrationProfile, ClassSection
from esp.program.models.class_ import ClassCategories
from esp.mailman import add_list_member, remove_list_member, list_contents

from django.conf import settings
import os

class StudentRegSanityController(object):

    default_options = {
        'directory': os.getenv("HOME"),
    }

    def __init__(self, program, **kwargs):
        self.program = program

        self.options = StudentRegSanityController.default_options.copy()
        self.options.update(kwargs)

    def sanitize_walkin(self, fake=True, csvwriter=None, csvlog=False, directory=None):
        """Checks for Student Registrations made for walk-in classes. If fake=False, will remove them."""
        category_walkin = ClassCategories.objects.get(category="Walk-in Activity")
        if csvlog and not(fake) and csvwriter is None:
            import csv
            if directory is None: directory = self.options['directory']
            filefullname = os.path.join(directory, 'sanitize_walkins_log.csv')
            with open(filefullname, 'a', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                return self._run_walkin_check(csvwriter, category_walkin, fake, csvlog)
        return self._run_walkin_check(csvwriter, category_walkin, fake, csvlog)

    def _run_walkin_check(self, csvwriter, category_walkin, fake, csvlog):
        """Process walk-in class registrations."""
        if csvlog and not fake:
            csvwriter.writerow(['Sanitizing Walkins'])
            csvwriter.writerow(['Class Title', 'Scheduled at:', 'Student', 'Enrollment Type:'])
        walkins = self.program.classes().filter(category=category_walkin)
        report = []
        for w in walkins:
            for sec in w.get_sections():
                srs = sec.getRegistrations()
                report.append((sec, srs.count()))
                for sr in srs:
                    if not fake:
                        if csvlog:
                            csvwriter.writerow([w.title(), ', '.join(sec.friendly_times()), sr.user.name(), str(sr.relationship)])
                        sr.expire()
        logger.debug(report)
        logger.info("Walkins checked")
        if not fake:
            logger.info("Please re-run self.initialize() to update.")
        return report

    def sanitize_lunch(self, csvlog=False, fake = True, csvwriter=None, directory=None):
        """Checks to see if any students have registrations for lunch. If fake=False, removes them."""
        if csvlog and not(fake) and csvwriter is None:
            import csv
            if directory is None: directory = self.options['directory']
            filefullname = os.path.join(directory, 'sanitize_lunch_log.csv')
            with open(filefullname, 'a', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                return self._run_lunch_check(csvwriter, fake, csvlog)
        return self._run_lunch_check(csvwriter, fake, csvlog)

    def _run_lunch_check(self, csvwriter, fake, csvlog):
        """Process lunch block registrations."""
        if csvlog and not fake:
            csvwriter.writerow(['Sanitizing Lunch Blocks'])
            csvwriter.writerow(['Lunch Block', 'Student', 'Enrollment Type:'])
        category_lunch = ClassCategories.objects.get(category="Lunch")
        lunchblocks = self.program.classes().filter(category=category_lunch)
        report = []
        for l in lunchblocks:
            srs = l.getRegistrations()
            report.append((l, srs.count()))
            if not fake:
                for sr in srs:
                    if csvlog: csvwriter.writerow([l.title(), sr.user.name(), str(sr.relationship)])
                    sr.expire()
        logger.debug(report)
        logger.info("Lunch checked.")
        if not fake:
            logger.info("Please re-run self.initialize() to update.")
        return report

    def sanitize(self, checks=None, fake=True, csvlog=True, directory=None):
        """Runs some checks on Student Registration. Enter in the checks you'd like to run as a list of strings.
        Checks that currently exist:
            -antiwalk-in: Checks for Student Registrations made for walk-in classes. Can remove them.
            -antilunch: Checks for Student Registrations made for lunch. Can remove them.
        Example syntax: self.sanitize(['antiwalk-in'])
        Run self.sanitize('--help') for more information
        Set fake=False if you actually want something to happen.
        Set csvlog=False if you don't want a log of what was done
        Set directory to where you'd like the csvlog filed saved (if csvlog=False, does nothing)"""
        if checks is None:
            print("You didn't enter a check! Please enter the checks you'd like to run as a list of strings. Run self.sanitize('--help') for more information!")
            return None
        if checks=='--help':
            print('Sanitize - a module used to clear up oddities in Student Registrations.')
            print("Syntax: self.sanitize(['check1', 'check2', 'check3'], fake=False, csvlog=True, directory='" + self.options['directory'] + "')")
            print('')
            print('-------------Current Checks----------------')
            print('antiwalk-in: Checks for Student Registrations made for walk-in classes. If fake=False, will remove them.')
            print('antilunch: Checks for Student Registrations made for lunch. If fake=False, will remove them.')
            print('-------------Known Bugs-----------------')
            print("Guys, I'm not course 6 for a reason~shulinye")
            return None
        if isinstance(checks, str):
            checks = [checks]
        if csvlog:
            import csv
            if directory is None: directory = self.options['directory']
            filefullname = os.path.join(directory, datetime.now().strftime("%Y-%m-%d_") + 'sanitize_log.csv')
            with open(filefullname, 'a', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                return self._run_sanitize_checks(checks, fake, csvlog, csvwriter)
        return self._run_sanitize_checks(checks, fake, csvlog, None)

    def _run_sanitize_checks(self, checks, fake, csvlog, csvwriter):
        """Run the requested sanitize checks."""
        self.reports = {}
        for ck in checks:
            logger.debug("Now running " + ck)
            if ck == 'antiwalk-in':
                self.reports['walkin'] = self.sanitize_walkin(fake = fake, csvwriter = csvwriter, csvlog=csvlog)
            if ck == 'antilunch':
                self.reports['antilunch'] = self.sanitize_lunch(fake = fake, csvwriter = csvwriter, csvlog=csvlog)
        return self.reports
