
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
from esp.program.modules.base import ProgramModuleObj, needs_student, needs_admin, main_call, aux_call
from esp.web.util        import render_to_response
from esp.program.modules.forms.satprep import SATPrepInfoForm
from esp.program.models import SATPrepRegInfo
from esp.dbmail.models import MessageRequest
from esp.users.models   import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from django.db.models.query   import Q
from esp.dbmail.models import ActionHandler
from django.template import Template
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from esp.middleware import ESPError

class CommModule(ProgramModuleObj):
    """ Want to email all ESP students within a 60 mile radius of NYC?
    How about emailing all esp users within a 30 mile radius of New Hampshire whose last name contains 'e' and 'a'?
    Do that and even more useful things in the communication panel.
    """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Communications Panel for Admin",
            "link_title": "Communications Panel",
            "module_type": "manage",
            "seq": 10
            }

    @aux_call
    @needs_admin
    def commprev(self, request, tl, one, two, module, extra, prog):
        from esp.users.models import PersistentQueryFilter
        from django.conf import settings

        filterid, listcount, subject, body = [request.POST['filterid'],
                                              request.POST['listcount'],
                                              request.POST['subject'],
                                              request.POST['body']    ]

        # Set From address
        if request.POST.has_key('from') and \
           len(request.POST['from'].strip()) > 0:
            fromemail = request.POST['from']
        else:
            # String together an address like username@esp.mit.edu
            fromemail = '%s@%s' % (request.user.username, settings.SITE_INFO[1])
        
        # Set Reply-To address
        if request.POST.has_key('replyto') and len(request.POST['replyto'].strip()) > 0:
            replytoemail = request.POST['replyto']
        else:
            replytoemail = fromemail

        try:
            filterid = int(filterid)
        except:
            raise ESPError(), "Corrupted POST data!  Please contact us at esp-web@mit.edu and tell us how you got this error, and we'll look into it."

        userlist = PersistentQueryFilter.getFilterFromID(filterid, ESPUser).getList(ESPUser)

        try:
            firstuser = userlist[0]
        except:
            raise ESPError(), "You seem to be trying to email 0 people!  Please go back, edit your search, and try again."

        #   If they were trying to use HTML, don't sanitize the content.
        if '<html>' not in body:
            htmlbody = body.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br />')
        else:
            htmlbody = body
            
        esp_firstuser = ESPUser(firstuser)
        contextdict = {'user'   : ActionHandler(esp_firstuser, esp_firstuser),
                       'program': ActionHandler(self.program, esp_firstuser) }
        renderedtext = Template(htmlbody).render(Context(contextdict))
        
        return render_to_response(self.baseDir()+'preview.html', request,
                                  (prog, tl), {'filterid': filterid,
                                               'listcount': listcount,
                                               'subject': subject,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'body': body,
                                               'renderedtext': renderedtext})


    @aux_call
    @needs_admin
    def commfinal(self, request, tl, one, two, module, extra, prog):
        from esp.dbmail.models import MessageRequest
        from esp.users.models import PersistentQueryFilter
        
        announcements = self.program_anchor_cached().tree_create(['Announcements'])
        filterid, fromemail, replytoemail, subject, body = [
                                    request.POST['filterid'],
                                    request.POST['from'],
                                    request.POST['replyto'],
                                    request.POST['subject'],
                                    request.POST['body']    ]
        
        try:
            filterid = int(filterid)
        except:
            raise ESPError(), "Corrupted POST data!  Please contact us at esp-web@mit.edu and tell us how you got this error, and we'll look into it."
        
        filterobj = PersistentQueryFilter.getFilterFromID(filterid, ESPUser)

        variable_modules = {'user': request.user, 'program': self.program}

        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = subject,
                                                      recipients = filterobj,
                                                      sender     = fromemail,
                                                      creator    = request.user,
                                                      msgtext    = body,
                                                      special_headers_dict
                                                                 = { 'Reply-To': replytoemail, }, )

        newmsg_request.save()

        foo = MessageRequest.objects.all()[0]

        # now we're going to process everything
        # nah, we'll do this later.
        #newmsg_request.process()

        numusers = filterobj.getList(ESPUser).count()

        from django.conf import settings
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            est_time = settings.EMAILTIMEOUT * len(users)
        else:
            est_time = 1.5 * numusers
            

        #        assert False, self.baseDir()+'finished.html'
        return render_to_response(self.baseDir()+'finished.html', request,
                                  (prog, tl), {'time': est_time})


    @aux_call
    @needs_admin
    def commstep2(self, request, tl, one, two, module, extra, prog):
        pass

    
    @aux_call
    @needs_admin
    def commpanel_old(self, request, tl, one, two, module, extra, prog):
        from esp.users.views     import get_user_list
        filterObj, found = get_user_list(request, self.program.getLists(True))

        if not found:
            return filterObj

        listcount = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()

        return render_to_response(self.baseDir()+'step2.html', request,
                                  (prog, tl), {'listcount': listcount,
                                               'filterid': filterObj.id })

    @main_call
    @needs_admin
    def commpanel(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['program'] = prog
        
        #   Parameters
        user_types = ['students', 'teachers', 'volunteers']
        preferred_lists = ['enrolled', 'studentfinaid', 'student_profile', 'class_approved', 'lotteried_students',  'teacher_profile', 'class_proposed', 'volunteer_all']
        global_categories = [('Student', 'students'), ('Teacher', 'teachers'), ('Guardian', 'parents'), ('Educator', 'parents'), ('Volunteer', 'volunteers')]
        
        def map_category_bwd(cat):
            for pair in global_categories:
                if cat == pair[1]:
                    return pair[0]
        def get_recipient_type(list_name):
            for user_type in user_types:
                raw_lists = getattr(prog, user_type)(True)
                if list_name in raw_lists:
                    return user_type
        
        #   If list information was submitted, continue to prepare a message
        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = {}
            for key in request.POST:
                data[key] = request.POST[key]
                
            ##  Handle "basic list" submissions
            if 'base_list' in data and 'recipient_type' in data:
        
                usc = UserSearchController()
                
                #   Get the program-specific part of the query (e.g. which list to use)
                if data['recipient_type'] not in user_types:
                    recipient_type = 'any'
                    q_program = Q()
                else:
                    if data['base_list'].startswith('all'):
                        q_program = Q()
                        recipient_type = map_category_bwd(data['recipient_type'])
                    else:
                        program_lists = getattr(prog, data['recipient_type'])(QObjects=True)
                        q_program = program_lists[data['base_list']]
                        """ Some program queries rely on UserBits, and since user types are also stored in
                            UserBits we cannot store both of these in a single Q object.  To compensate, we
                            ignore the user type when performing a program-specific query.  """
                        recipient_type = 'any'
                    
                #   Get the user-specific part of the query (e.g. ID, name, school)
                q_extra = usc.query_from_criteria(recipient_type, data)
                
                #   Get a persistent filter object combining these query criteria
                filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q_extra & q_program)
                filterObj.useful_name = 'Program list: %s' % data['base_list']
                filterObj.save()
                
                context['filterid'] = filterObj.id
                context['listcount'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
                return render_to_response(self.baseDir()+'step2.html', request, (prog, tl), context)
                
            ##  Handle "combination list" submissions
            elif 'combo_base_list' in data:
                usc = UserSearchController()
                
                #   Get an initial query from the supplied base list
                recipient_type, list_name = data['combo_base_list'].split(':')
                if list_name.startswith('all'):
                    q_program = Q()
                else:
                    q_program = getattr(prog, recipient_type)(QObjects=True)[list_name]
                
                #   Apply Boolean filters
                #   Base list will be intersected with any lists marked 'AND', and then unioned
                #   with any lists marked 'OR'.
                checkbox_keys = map(lambda x: x[9:], filter(lambda x: x.startswith('checkbox_'), data.keys()))
                and_keys = map(lambda x: x[4:], filter(lambda x: x.startswith('and_'), checkbox_keys))
                or_keys = map(lambda x: x[3:], filter(lambda x: x.startswith('or_'), checkbox_keys))
                not_keys = map(lambda x: x[4:], filter(lambda x: x.startswith('not_'), checkbox_keys))
                
                for and_list_name in and_keys:
                    user_type = get_recipient_type(and_list_name)
                    if user_type:
                        if and_list_name not in not_keys:
                            q_program = q_program & (getattr(prog, user_type)(QObjects=True)[and_list_name])
                        else:
                            q_program = q_program & (~getattr(prog, user_type)(QObjects=True)[and_list_name])
                for or_list_name in or_keys:
                    user_type = get_recipient_type(or_list_name)
                    if user_type:
                        if or_list_name not in not_keys:
                            q_program = q_program | (getattr(prog, user_type)(QObjects=True)[or_list_name])
                        else:
                            q_program = q_program | (~getattr(prog, user_type)(QObjects=True)[or_list_name])
                        
                #   Get the user-specific part of the query (e.g. ID, name, school)
                q_extra = usc.query_from_criteria(map_category_bwd(recipient_type), data)
                
                #   Get a persistent filter object combining these query criteria
                filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q_extra & q_program)
                filterObj.useful_name = 'Custom user list'
                filterObj.save()
                
                context['filterid'] = filterObj.id
                context['listcount'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
                return render_to_response(self.baseDir()+'step2.html', request, (prog, tl), context)
                
            elif 'msgreq_id' in data:
                ##  Prepare a message starting from an earlier request
                msgreq = MessageRequest.objects.get(id=data['msgreq_id'])
                context['filterid'] = msgreq.recipients.id
                context['listcount'] = msgreq.recipients.getList(ESPUser).count()
                context['from'] = msgreq.sender
                context['subject'] = msgreq.subject
                context['replyto'] = msgreq.special_headers_dict.get('Reply-To', '')
                context['body'] = msgreq.msgtext
                return render_to_response(self.baseDir()+'step2.html', request, (prog, tl), context)
                
            else:
                raise ESPError(True), 'What do I do without knowing what kind of users to look for?'
        
        #   Otherwise, render a page that shows the list selection options
        category_lists = {}
        list_descriptions = prog.getListDescriptions()
        
        #   Add in program-specific lists for most common user types
        for user_type in user_types:
            raw_lists = getattr(prog, user_type)(True)
            category_lists[user_type] = [{'name': key, 'list': raw_lists[key], 'description': list_descriptions[key]} for key in raw_lists]
            for item in category_lists[user_type]:
                if item['name'] in preferred_lists:
                    item['preferred'] = True
                    
        #   Add in global lists for each user type
        for cat_pair in global_categories:
            key = cat_pair[0].lower() + 's'
            if cat_pair[1] not in category_lists:
                category_lists[cat_pair[1]] = []
            category_lists[cat_pair[1]].insert(0, {'name': 'all_%s' % key, 'list': ESPUser.getAllOfType(cat_pair[0]), 'description': 'All %s in the database' % key, 'preferred': True, 'all_flag': True})
        
        #   Add in mailing list accounts
        category_lists['emaillist'] = [{'name': 'all_emaillist', 'list': Q(password = 'emailuser'), 'description': 'Everyone signed up for the mailing list', 'preferred': True}]
        
        context['lists'] = category_lists
        context['all_list_names'] = []
        for category in category_lists:
            for item in category_lists[category]:
                context['all_list_names'].append(item['name'])
        
        return render_to_response(self.baseDir()+'commpanel_new.html', request, (prog, tl), context)

    @aux_call
    @needs_admin
    def maincomm2(self, request, tl, one, two, module, extra, prog):

        filterid, listcount, fromemail, replytoemail, subject, body = [
                                                         request.POST['filterid'],
                                                         request.POST['listcount'],
                                                         request.POST['from'],
                                                         request.POST['replyto'],
                                                         request.POST['subject'],
                                                         request.POST['body']    ]

        return render_to_response(self.baseDir()+'step2.html', request,
                                  (prog, tl), {'listcount': listcount,
                                               'filterid': filterid,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'subject': subject,
                                               'body': body})

    @needs_student
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            form = SATPrepInfoForm(request.POST)

            if form.is_valid():
                reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
                form.instance = reginfo
                form.save()

                return self.goToCore(tl)
        else:
            satPrep = SATPrepRegInfo.getLastForProgram(request.user, prog)
            form = SATPrepInfoForm(instance = satPrep)

        return render_to_response('program/modules/satprep_stureg.html', request, (prog, tl), {'form':form})



    class Meta:
        abstract = True

