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

from esp.program.tests import ProgramFrameworkTest

class AvailabilityModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 1, 'classes_per_teacher': 2, 'sections_per_class': 1
            } )
        super(AvailabilityModuleTest, self).setUp(*args, **kwargs)

        # Get and remember the instance of AvailabilityModule
        am = ProgramModule.objects.get(handler='AvailabilityModule', module_type='teach')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, am)
        self.moduleobj.user = self.teachers[0]

        # Set the section durations to 0:50 and 1:50
        sec = self.program.sections()[0]
        sec.duration = '0.83'
        sec.save()
        sec = self.program.sections()[1]
        sec.duration = '1.83'
        sec.save()

    def runTest(self):
        # Now we have a program with 3 timeslots, 1 teacher, and 2 classes.
        # Grab the timeslots
        timeslots = self.program.getTimeSlots().values_list( 'id', flat=True )

        # Check that the teacher starts out without availability set
        self.assertTrue( not self.moduleobj.isCompleted() )

        # Log in as the teacher
        self.assertTrue( self.client.login( username=self.teachers[0].username, password='password' ), "Couldn't log in as teacher %s" % self.teachers[0].username )

        # Submit availability, checking results each time
        # Available for one timeslot
        response = self.client.post( self.moduleobj.get_full_path(), data={ 'timeslots': timeslots[:1] } )
        self.assertTrue( response.status_code == 302 )
        self.assertTrue( not self.moduleobj.isCompleted() )
        # Two timeslots
        response = self.client.post( self.moduleobj.get_full_path(), data={ 'timeslots': timeslots[:2] } )
        self.assertTrue( response.status_code == 302 )
        self.assertTrue( not self.moduleobj.isCompleted() )
        # Three timeslots
        response = self.client.post( self.moduleobj.get_full_path(), data={ 'timeslots': timeslots } )
        self.assertTrue( response.status_code == 302 )
        self.assertTrue( self.moduleobj.isCompleted() )
