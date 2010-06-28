
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.http      import HttpResponse
from esp.users.views  import search_for_user
from esp.program.models import SplashInfo
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.users.models import ESPUser
from datetime         import datetime
from esp.web.util     import render_to_response
from esp.datatree.models import *
from esp.users.models import UserBit
from datetime         import datetime
from django.db.models.query   import Q
from esp.accounting_docs.models import Document, MultipleDocumentError
from django.template.loader import select_template

class OnsitePrintSchedules(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Automatically Print Schedules for Onsite Reg",
            "link_title": "Automatically Print Schedules",
            "module_type": "onsite",
            "seq": 10000
            }

    @main_call
    @needs_onsite
    def printschedules(self, request, tl, one, two, module, extra, prog):
        " A link to print a schedule. "
        if not request.GET.has_key('sure') and not request.GET.has_key('gen_img'):
            printers = [ x.name for x in GetNode('V/Publish/Print').children() ]

            return render_to_response(self.baseDir()+'instructions.html',
                                    request, (prog, tl), {'printers': printers})

        if request.GET.has_key('sure'):
            return render_to_response(self.baseDir()+'studentschedulesrenderer.html',
                            request, (prog, tl), {})

        verb_path = 'V/Publish/Print'
        if extra and extra != '':
            verb_path = "%s/%s" % (verb_path, extra)

        verb  = GetNode(verb_path)
        qsc   = self.program_anchor_cached().tree_create(['Schedule'])

        Q_qsc  = Q(qsc  = qsc.id)
        Q_verb = Q(verb__in = [ verb.id ] + list( verb.children() ) )
        
        ubits = UserBit.valid_objects().filter(Q_qsc & Q_verb).order_by('startdate')[:1]
        
        for ubit in ubits:
            ubit.enddate = datetime.now()
            ubit.save()

        # get students
        old_students = set([ ESPUser(ubit.user) for ubit in ubits ])

        response = ProgramPrintables.get_student_schedules(request, list(old_students), prog, onsite=True)       
        # set the refresh rate
        #response['Refresh'] = '2'

        return response

    def studentschedule(self, request, *args, **kwargs):
        request.GET = {'extra': str(285), 'op':'usersearch',
                       'userid': str(self.user.id) }

        module = [module for module in self.program.getModules('manage')
                  if type(module) == ProgramPrintables        ][0]

        module.user = self.user
        module.program = self.program
        return module.studentschedules(request, *args, **kwargs)

        
