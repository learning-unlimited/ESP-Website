__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""
from django.db.models.query import Q

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, needs_admin
from esp.cache           import cache_function
from esp.web.util        import render_to_response

from esp.program.models import ClassSubject, ClassFlag, ClassFlagType, flag_types
from esp.users.models import ESPUser

class ClassFlagModule(ProgramModuleObj):
    doc = """ Flag classes, such as for further review.  Find all classes matching certain flags, and so on. """
    @classmethod
    def module_properties(cls):
        return {
                "admin_title": "Class Flags",
                "link_title": "Manage Class Flags",
                "module_type": "manage",
                "seq": 100,
                }

    class Meta:
        abstract = True
    
    def teachers(self, QObject = False):
        flag_types = flag_types(self.program)
        t = {}
        for flag_type in flag_types:
            q = Q(classsubject__classflag__flag_type=flag_type.id)
            if QObject:
                t['flag_%s' % flag_type.id] = q
            else:
                t['flag_%s' % flag_type.id] = ESPUser.objects.filter(q)
        return t
    
    def teacherDesc(self):
        flag_types = flag_types(self.program)
        descs = {}
        for flag_type in flag_types:
            descs['flag_%s' % flag_type.id] = """Teachers who have a class with the "%s" flag.""" % flag_type.name
        return descs
    
    @main_call
    @needs_admin
    def classflags(self, request, tl, one, two, module, extra, prog):
        if request.method == 'GET':
            # We should display the query builder interface.
            fts = flag_types(self.program)
            context = { 'flag_types': fts }
            return render_to_response(self.baseDir()+'flag_query_builder.html', request, context)
        elif request.method == 'POST':
            # They've sent a query, let's process it.
            pass

