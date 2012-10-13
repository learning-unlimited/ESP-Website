
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.users.models    import ESPUser

class FormstackAppModule(ProgramModuleObj, module_ext.FormstackAppSettings):
    """
    Student application module for Junction.

    Not to be confused with StudentJunctionAppModule, the app questions module.
    """

    @classmethod
    def module_properties(cls):
        return [{
            "admin_title": "Formstack Application Module",
            "link_title": "Student Application",
            "module_type": "learn",
            "seq": 10,
            "required": True,
            }]

    def extensions(self):
        """ This function gives all the extensions...that is, models that act on the join of a program and module."""
        return []

    def students(self, QObject = False):
        # TODO (below copied from studentclassregmodule)

        # from django.db.models import Q

        # now = datetime.now()

        # Enrolled = Q(studentregistration__relationship__name='Enrolled')
        # Par = Q(studentregistration__section__parent_class__parent_program=self.program)
        # Unexpired = Q(studentregistration__end_date__gte=now, studentregistration__start_date__lte=now) # Assumes that, for all still-valid registrations, we don't care about startdate, and enddate is null.
        
        # if QObject:
        #     retVal = {'enrolled': self.getQForUser(Enrolled & Par & Unexpired), 'classreg': self.getQForUser(Par & Unexpired)}
        # else:
        #     retVal = {'enrolled': ESPUser.objects.filter(Enrolled & Par & Unexpired).distinct(), 'classreg': ESPUser.objects.filter(Par & Unexpired).distinct()}

        # allowed_student_types = Tag.getTag("allowed_student_types", target = self.program)
        # if allowed_student_types:
        #     allowed_student_types = allowed_student_types.split(",")
        #     for stutype in allowed_student_types:
        #         VerbParent = Q(userbit__verb__parent=GetNode("V/Flags/UserRole"))
        #         VerbName = Q(userbit__verb__name=stutype)
        #         if QObject:
        #             retVal[stutype] = self.getQForUser(Par & Unexpired & Reg & VerbName & VerbParent)
        #         else:
        #             retVal[stutype] = ESPUser.objects.filter(Par & Unexpired & Reg & VerbName & VerbParent).distinct()

        # return retVal
        result = {}

        apps = self.get_student_apps()
        result['applied'] = set(app.user for app in apps)

        return result

    def studentDesc(self):
        # TODO (below copied from studentclassregmodule)

        #   Label these heading nicely like the user registration form
        # role_choices = ESPUser.getAllUserTypes()
        # role_dict = {}
        # for item in role_choices:
        #     role_dict[item[0]] = item[1]
    
        # result = {'classreg': """Students who signed up for at least one class""",
        #           'enrolled': """Students who are enrolled in at least one class"""}
        # allowed_student_types = Tag.getTag("allowed_student_types", target = self.program)
        # if allowed_student_types:
        #     allowed_student_types = allowed_student_types.split(",")
        #     for stutype in allowed_student_types:
        #         if stutype in role_dict:
        #             result[stutype] = role_dict[stutype]

        # return result
        result = {}
        result['applied'] = """Students who submitted an application"""
        return result
    
    def isCompleted(self):
        # TODO (below copied from studentclassregmodule)

        # return (len(get_current_request().user.getSectionsFromProgram(self.program)[:1]) > 0)
        return False

    def deadline_met(self, extension=None):
        # TODO (below copied from studentclassregmodule)

        # #   Allow default extension to be overridden if necessary
        # if extension is not None:
        #     return super(StudentClassRegModule, self).deadline_met(extension)
        # else:
        #     return super(StudentClassRegModule, self).deadline_met('/Classes/OneClass')
        return True

    def prepare(self, context={}):
        # TODO (below copied from studentclassregmodule)

        # from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC
        # verbs = RTC.getVisibleRegistrationTypeNames(prog=self.program)
        # regProf = RegistrationProfile.getLastForProgram(get_current_request().user, self.program)
        # timeslots = self.program.getTimeSlotList(exclude_compulsory=False)
        # classList = ClassSection.prefetch_catalog_data(regProf.preregistered_classes(verbs=verbs))

        # prevTimeSlot = None
        # blockCount = 0

        # if not isinstance(get_current_request().user, ESPUser):
        #     user = ESPUser(get_current_request().user)
        # else:
        #     user = get_current_request().user
            
        # is_onsite = user.isOnsite(self.program)
        # scrmi = self.program.getModuleExtension('StudentClassRegModuleInfo')
        # # Hack, to hide the Saturday night timeslots from grades 7-8
        # if not is_onsite and not user.getGrade() > 8:
        #     timeslots = [x for x in timeslots if x.start.hour < 19]
        
        # #   Filter out volunteer timeslots
        # timeslots = [x for x in timeslots if x.event_type.description != 'Volunteer']
        
        # schedule = []
        # timeslot_dict = {}
        # for sec in classList:
        #     #   TODO: Fix this bit (it was broken, and may need additional queries
        #     #   or a parameter added to ClassRegModuleInfo).
        #     show_changeslot = False
            
        #     #   Get the verbs all the time in order for the schedule to show
        #     #   the student's detailed enrollment status.  (Performance hit, I know.)
        #     #   - Michael P, 6/23/2009
        #     #   if scrmi.use_priority:
        #     sec.verbs = sec.getRegVerbs(user, allowed_verbs=verbs)
            
        #     for mt in sec.get_meeting_times():
        #         section_dict = {'section': sec, 'changeable': show_changeslot}
        #         if mt.id in timeslot_dict:
        #             timeslot_dict[mt.id].append(section_dict)
        #         else:
        #             timeslot_dict[mt.id] = [section_dict]
                    
        # user_priority = user.getRegistrationPriorities(self.program, [t.id for t in timeslots])
        # for i in range(len(timeslots)):
        #     timeslot = timeslots[i]
        #     daybreak = False
        #     if prevTimeSlot != None:
        #         if not Event.contiguous(prevTimeSlot, timeslot):
        #             blockCount += 1
        #             daybreak = True

        #     if timeslot.id in timeslot_dict:
        #         cls_list = timeslot_dict[timeslot.id]
        #         schedule.append((timeslot, cls_list, blockCount + 1, user_priority[i]))
        #     else:                
        #         schedule.append((timeslot, [], blockCount + 1, user_priority[i]))

        #     prevTimeSlot = timeslot
                
        # context['num_classes'] = len(classList)
        # context['timeslots'] = schedule
        # context['use_priority'] = scrmi.use_priority
        # context['allow_removal'] = self.deadline_met('/Removal')

        return context

    @main_call
    @needs_student
    def studentapp(self, request, tl, one, two, module, extra, prog):
        # TODO: deadlines
        args = {}
        if self.username_field is not None:
            # prepopulate username field
            field_name = 'field{}'.format(self.username_field)
            args[field_name] = request.user.username
        form_embed = self.form.get_javascript(args)
        context = {}
        context['form_embed'] = form_embed
        return render_to_response(self.baseDir()+'studentapp.html',
                                  request, (prog, tl), context)

    @aux_call
    @needs_admin
    def listapps(self, request, tl, one, two, module, extra, prog):
        apps = self.get_student_apps()
        context = {}
        context['apps'] = apps
        return render_to_response(self.baseDir()+'listapps.html',
                                  request, (prog, tl), context)

    @aux_call
    @needs_admin
    def viewapp(self, request, tl, one, two, module, extra, prog):
        apps = self.get_student_apps()
        if extra:
            matching_apps = [app for app in apps if app.id == int(extra)]
        else:
            matching_apps = []
        if matching_apps:
            app = matching_apps[0]
            context = {}
            context['app'] = app
            return render_to_response(self.baseDir()+'viewapp.html',
                                      request, (prog, tl), context)

    @aux_call
    @needs_teacher
    def teacherviewapp(self, request, tl, one, two, module, extra, prog):
        apps = self.get_student_apps()
        if extra:
            matching_apps = [app for app in apps if app.id == int(extra)]
        else:
            matching_apps = []
        if matching_apps:
            app = matching_apps[0]
            context = {}
            context['app'] = app
            return render_to_response(self.baseDir()+'teacherviewapp.html',
                                      request, (prog, tl), context)

    def getNavBars(self):
        print 'I wonder if getNavBars gets called anywhere'
        return []
        # if super(StudentClassRegModule, self).deadline_met('/Catalog'):
        #     return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
        #               'text': '%s Catalog' % ( self.program.niceSubName() ) }]
        
        # else:
        #     return []

    class Meta:
        abstract = True

