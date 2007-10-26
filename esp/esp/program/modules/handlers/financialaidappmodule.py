
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.datatree.models import GetNode, DataTree
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit, User
from esp.db.models       import Q
from django.template.loader import get_template
from esp.program.models  import FinancialAidRequest
from django              import newforms as forms


# student class picker module
class FinancialAidAppModule(ProgramModuleObj):

    def students(self, QObject = False):
        Q_students = Q(financialaidrequest__program = self.program)

        Q_students_complete = Q(financialaidrequest__done = True)

        if QObject:
            return {'studentfinaid_complete': Q_students & Q_students_complete,
                    'studentfinaid':          Q_students}
        else:
            return {'studentfinaid_complete': User.objects.filter(Q_students & Q_students_complete),
                    'studentfinaid':          User.objects.filter(Q_students)}
        


    def studentDesc(self):
        return {'studentfinaid_complete': """Students who have completed the student financial aid applications.""",
                'studentfinaid':          """Students who have started the student financial aid applications."""}
    
    def isCompleted(self):
        return self.user.financialaidrequest_set.all().filter(program = self.program, done = True).count() > 0

    @needs_student
    @meets_deadline()
    def finaid(self,request, tl, one, two, module, extra, prog):
        """
        Student financial aid requests.
        This template will redirect the person to an HTTPS address.
        """

        return render_to_response(self.baseDir()+'aid_direct.html',
                                  request,
                                  (self.program, tl),
                                  {})
    
    @needs_student
    @meets_deadline()
    def finaid_app(self,request, tl, one, two, module, extra, prog):
        """
        A way for a student to apply for financial aid.
        """
        
        app, created = FinancialAidRequest.objects.get_or_create(user = self.user,
                                                                program = self.program)

        Form = forms.form_for_model(FinancialAidRequest)
        
        if request.method == 'POST':
            form = Form(request.POST, initial = app.__dict__)
            if form.is_valid():
                app.__dict__.update(form.clean_data)
                if request.POST['submitform'].lower() == 'complete':
                    app.done = True
                    
                if request.POST['submitform'].lower() == 'mark as unfinished':
                    app.done = False
                    
                # Automatically accept apps for people with subsidized lunches
                if app.reduced_lunch:
                    from datetime import datetime
                    from django.core.mail import send_mail
                    app.approved = datetime.now()
                    send_mail( '%s %s received Financial Aid for %s' % (request.user.first_name, 
                                                                       request.user.last_name,
                                                                       prog.niceName()), 
                               '%s %s received Financial Aid for %s on %s, for stating that they receive a free or reduced-price lunch.' % (request.user.first_name, 
                                                                       request.user.last_name,
                                                                       prog.niceName(),
                                                                       str(app.approved)), 
                               'web@esp.mit.edu',
                               [ prog.director_email ] )
                              
                app.save()
                return self.goToCore(tl)
            
        else:
            form = Form(initial = app.__dict__)


        return render_to_response(self.baseDir()+'application.html',
                                  request,
                                  (self.program, tl),
                                  {'form': form,'app':app})

