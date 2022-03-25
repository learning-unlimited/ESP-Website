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
        closeatend = False
        category_walkin = ClassCategories.objects.get(category="Walk-in Activity")
        if csvlog and not(fake): #If I'm actually doing things, and I want a log....
            import csv
            if csvwriter==None:
                closeatend = True
                if directory==None: directory = self.options['directory']
                filefullname = directory +'/santitize_walkins_log.csv'
                csvfile = open(filefullname, 'ab+')
                csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Sanitizing Walkins'])
            csvwriter.writerow(['Class Title', 'Scheduled at:', 'Student', 'Enrollment Type:'])
        walkins=self.program.classes().filter(category=category_walkin)
        report = []
        for w in walkins:
            for sec in w.get_sections():
                srs = sec.getRegistrations()
                report.append((sec, srs.count()))

        for sr in srs:
            if not fake:
                if csvlog: csvwriter.writerow([w.title().encode('ascii', 'ignore'), ', '.join(sec.friendly_times()), sr.user.name().encode('ascii', 'ignore'), sr.relationship.__unicode__().encode('ascii', 'ignore')])
                sr.expire()
        logger.debug(report)
        if closeatend: csvfile.close()
        logger.info("Walkins checked")
        if not fake: "Please re-run self.initalize() to update."
        return report

    def sanitize_lunch(self, csvlog=False, fake = True, csvwriter=None, directory=None):
        """Checks to see if any students have registrations for lunch. If fake=False, removes them."""
        closeatend = False
        if csvlog and not(fake): #If I'm actually doing things, and I want a log....
            import csv
            if csvwriter==None:
                closeatend = True
                if directory==None: directory = self.options['directory']
                filefullname = directory +'/santitize_lunch_log.csv'
                csvfile = open(filefullname, 'ab+')
                csvwriter = csv.writer(csvfile)
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
                    if csvlog: csvwriter.writerow([l.title().encode('ascii', 'ignore'), sr.user.name().encode('ascii', 'ignore'), sr.relationship.__unicode__().encode('ascii', 'ignore')])
                    sr.expire()
        logger.debug(report)
        if closeatend: csvfile.close()
        logger.info("Lunch checked.")
        if not fake: "Please re-run self.initalize() to update."
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
        if checks==None:
            print "You didn't enter a check! Please enter the checks you'd like to run as a list of strings. Run self.sanitize('--help') for more information!"
            return None
        if checks=='--help':
            print 'Sanitize - a module used to clear up oddities in Student Registrations.'
            print "Syntax: self.sanitize(['check1', 'check2', 'check3'], fake=False, csvlog=True, directory='" + self.options['directory'] + "')"
            print ''
            print '-------------Current Checks----------------'
            print 'antiwalk-in: Checks for Student Registrations made for walk-in classes. If fake=False, will remove them.'
            print 'antilunch: Checks for Student Registrations made for lunch. If fake=False, will remove them.'
            print '-------------Known Bugs-----------------'
            print "Guys, I'm not course 6 for a reason~shulinye"
            return None
        if isinstance(checks, basestring):
            checks = [checks]
        if csvlog:
            import csv
            if directory==None: directory = self.options['directory']
            filefullname = directory + '/'+ datetime.now().strftime("%Y-%m-%d_") + 'santitize_log.csv'
            csvfile = open(filefullname, 'ab+')
            csvwriter = csv.writer(csvfile)
        self.reports = {}
        for ck in checks:
            logger.debug("Now running " + ck)
            if ck == 'antiwalk-in':
                self.reports['walkin'] = self.sanitize_walkin(fake = fake, csvwriter = csvwriter if csvlog else None, csvlog=csvlog)
            if ck == 'antilunch':
                self.reports['antilunch'] = self.sanitize_lunch(fake = fake, csvwriter = csvwriter if csvlog else None, csvlog=csvlog)
        if csvlog: csvfile.close()
        return self.reports
