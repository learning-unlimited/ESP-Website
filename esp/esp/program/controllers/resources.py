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

from django.db.models import ProtectedError

from esp.cal.models import Event
from esp.middleware import ESPError
from esp.resources.models import ResourceType, Resource
from esp.program.models import ClassSection

class ResourceController(object):
    """ Controller for managing program resources.

    This is merely a framework, and most functionality will be added
    in the future when the resources schema is revised.
    """

    def __init__(self, program, *args, **kwargs):
        self.program = program

    def delete_timeslot(self, id):
        #   delete timeslot
        ts = Event.objects.get(id=id)
        ts.delete()

    def add_or_edit_timeslot(self, form):
        """ form is a TimeslotForm object   """
        if form.cleaned_data['id'] is not None:
            new_timeslot = Event.objects.get(id=form.cleaned_data['id'])
        else:
            new_timeslot = Event()

        form.save_timeslot(self.program, new_timeslot)
        return new_timeslot

    def delete_restype(self, id):
        #   delete restype
        rt = ResourceType.objects.get(id=id)
        try:
            rt.delete()
        except ProtectedError:
            raise ESPError("This resource type can't be deleted because it has "
                           "already been requested. If you really want to "
                           "delete it, first go to the admin panel and delete "
                           "all ResourceRequests for this resource type.",
                           log=False)

    def add_or_edit_restype(self, form, choices = None):
        if form.cleaned_data['id'] is not None:
            new_restype = ResourceType.objects.get(id=form.cleaned_data['id'])
        else:
            new_restype = ResourceType()

        form.save_restype(self.program, new_restype, choices)
        return new_restype

    def delete_classroom(self, id):
        target_resource = Resource.objects.get(id=id)
        rooms = self.program.getClassrooms().filter(name=target_resource.name)
        #   unschedule sections scheduled in classroom
        secs = ClassSection.objects.filter(resourceassignment__resource__in=rooms).distinct()
        for sec in secs:
            sec.clearRooms()
            sec.clearFloatingResources()
            sec.meeting_times.clear()
        #   delete classroom with specified ID and associated resources
        for room in rooms:
            room.associated_resources().delete()
        rooms.delete()

    def add_or_edit_classroom(self, form, furnishings = None):
        form.save_classroom(self.program, furnishings = furnishings)

    def delete_equipment(self, id):
        #   delete this resource for all time blocks within the program
        rl = Resource.objects.get(id=id).identical_resources().filter(event__program=self.program)
        for r in rl:
            r.delete()
