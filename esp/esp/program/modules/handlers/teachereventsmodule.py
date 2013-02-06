
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.dbmail.models import send_mail
from django.db.models.query import Q
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode
from esp.cal.models import Event
from esp.users.models import ESPUser, UserBit, User
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.modules.forms.teacherevents import TimeslotForm
from datetime import datetime

class TeacherEventsModule(ProgramModuleObj):
    # Initialization
    def __init__(self, *args, **kwargs):
        super(TeacherEventsModule, self).__init__(*args, **kwargs)

    @property
    def qscs(self):
        if not hasattr(self, '_qscs'):
            self._qscs = {
                'interview': GetNode( self.program_anchor_cached().get_uri() + '/TeacherEvents/Interview' ),
                'training': GetNode( self.program_anchor_cached().get_uri() + '/TeacherEvents/Training' )
            }
        return self._qscs
    
    @property
    def reg_verb(self):
        if not hasattr(self, '_reg_verb'):
            self._reg_verb = GetNode('V/Flags/Registration/Teacher')
        return self._reg_verb
    
    # General Info functions
    @classmethod
    def module_properties(cls):
        return [ {
            "module_type": "teach",
            'required': False,
            'admin_title': 'Teacher Training and Interview Signups',
            'link_title': 'Sign up for Teacher Training and Interviews',
            'seq': 5,
        }, {
            "module_type": "manage",
            'required': False,
            'admin_title': 'Manage Teacher Training and Interviews',
            'link_title': 'Teacher Training and Interviews',
        } ]
    
    def teachers(self, QObject = False):
        """ Returns lists of teachers who've signed up for interviews and for teacher training. """
        
        if QObject is True:
            return {
                'interview': self.getQForUser(Q( userbit__qsc__parent = self.qscs['interview'] )),
                'training': self.getQForUser(Q( userbit__qsc__parent = self.qscs['training'] ))
            }
        else:
            return {
                'interview': ESPUser.objects.filter( userbit__qsc__parent = self.qscs['interview'] ).distinct(),
                'training': ESPUser.objects.filter( userbit__qsc__parent = self.qscs['training'] ).distinct()
            }

    def teacherDesc(self):
        return {
            'interview': """Teachers who have signed up for an interview.""",
            'training':  """Teachers who have signed up for teacher training.""",
        }
    
    # Helper functions
    def getTimes(self, type):
        """ Get events of the program's teacher interview/training slots. """
        return Event.objects.filter( anchor__parent=self.qscs[type] ).order_by('start')
    
    def bitsBySlot(self, anchor):
        return UserBit.objects.filter( UserBit.not_expired(), verb=self.reg_verb, qsc=anchor )
    
    def bitsByTeacher(self, user):
        return {
            'interview': UserBit.objects.filter( UserBit.not_expired(), verb=self.reg_verb, qsc__parent=self.qscs['interview'], user=user ),
            'training': UserBit.objects.filter( UserBit.not_expired(), verb=self.reg_verb, qsc__parent=self.qscs['training'], user=user ),
        }
    
    # Per-user info
    def isCompleted(self):
        """
        Return true iff user has signed up for everything possible.
        If there are teacher training timeslots, requires signing up for them.
        If there are teacher interview timeslots, requires those too.
        """
        bits = self.bitsByTeacher(get_current_request().user)
        return (self.getTimes('interview').count() == 0 or bits['interview'].count() > 0) and (self.getTimes('training').count() == 0 or bits['training'].count() > 0)
    
    # Views
    @main_call
    @needs_teacher
    @meets_deadline('/MainPage')
    def event_signup(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            form = TeacherEventSignupForm(self, request.POST)
            if form.is_valid():
                data = form.cleaned_data
                # Remove old bits
                [ ub.expire() for ub in UserBit.objects.filter(
                    Q(qsc__parent=self.qscs['interview']) | Q(qsc__parent=self.qscs['training']), UserBit.not_expired(),
                    user=request.user, verb=self.reg_verb ) ]
                # Register for interview
                if data['interview']:
                    ub, created = UserBit.objects.get_or_create( user=request.user, qsc=data['interview'], verb=self.reg_verb, defaults={'recursive':False} )
                    # Send the directors an e-mail
                    if self.program.director_email and (created or ub.enddate < datetime.now() ):
                        event_names = ' '.join([x.description for x in data['interview'].event_set.all()])
                        send_mail('['+self.program.niceName()+'] Teacher Interview for ' + request.user.first_name + ' ' + request.user.last_name + ': ' + event_names, \
                              """Teacher Interview Registration Notification\n--------------------------------- \n\nTeacher: %s %s\n\nTime: %s\n\n""" % \
                              (request.user.first_name, request.user.last_name, event_names) , \
                              ('%s <%s>' % (request.user.first_name + ' ' + request.user.last_name, request.user.email,)), \
                              [self.program.director_email], True)
                    if not created:
                        ub.enddate = datetime(9999,1,1) # Approximately infinity; see default value of UserBit.enddate
                        ub.save()
                # Register for training
                if data['training']:
                    ub, created = UserBit.objects.get_or_create( user=request.user, qsc=data['training'], verb=self.reg_verb, defaults={'recursive':False} )
                    if not created:
                        ub.enddate = datetime(9999,1,1) # Approximately infinity
                        ub.save()
                return self.goToCore(tl)
        else:
            data = {}
            bits = self.bitsByTeacher(request.user)
            if bits['interview'].count() > 0:
                data['interview'] = bits['interview'][0].qsc.id
            if bits['training'].count() > 0:
                data['training'] = bits['training'][0].qsc.id
            form = TeacherEventSignupForm(self, initial=data)
        return render_to_response( self.baseDir()+'event_signup.html', request, (prog, tl), {'prog':prog, 'form': form} )
    
    @main_call
    @needs_admin
    def teacher_events(self, request, tl, one, two, module, extra, prog):
        context = {}
        
        if request.method == 'POST':
            data = request.POST
            
            if data['command'] == 'delete':
                #   delete timeslot
                ts = Event.objects.get(id=data['id'])
                ts.delete()
                
            elif data['command'] == 'add':
                #   add/edit timeslot
                form = TimeslotForm(data)
                if form.is_valid():
                    new_timeslot = Event()
                    
                    # decide type
                    type = "training"
                    
                    if data.has_key('submit') and data['submit'] == "Add Interview":
                        type = "interview"
                    
                    form.save_timeslot(self.program, new_timeslot, type, self.qscs[type])
                else:
                    context['timeslot_form'] = form
        
        if 'timeslot_form' not in context:
            context['timeslot_form'] = TimeslotForm()
        
        interview_times = self.getTimes('interview').select_related('anchor__userbit_qsc__user')
        training_times = self.getTimes('training').select_related('anchor__userbit_qsc__user')
        
        for ts in list( interview_times ) + list( training_times ):
            ts.teachers = [ x.user.first_name + ' ' + x.user.last_name + ' <' + x.user.email + '>' for x in self.bitsBySlot( ts.anchor ) ]
        
        context['prog'] = prog
        context['interview_times'] = interview_times
        context['training_times'] = training_times
        
        return render_to_response( self.baseDir()+'teacher_events.html', request, (prog, tl), context )




    class Meta:
        abstract = True

