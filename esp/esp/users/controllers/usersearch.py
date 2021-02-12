__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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
from collections import defaultdict
from esp.users.models import ESPUser, ZipCode, PersistentQueryFilter, Record
from esp.middleware import ESPError
from esp.utils.web import render_to_response
from esp.program.models import Program, RegistrationType, StudentRegistration
from esp.dbmail.models import MessageRequest
from esp.utils.query_utils import nest_Q
from esp.cal.models import EventType

from django.db.models import Count
from django.db.models.query import Q
from django.contrib.auth.models import Group

import collections
import re

class UserSearchController(object):

    #   Static parameters
    preferred_lists = ['enrolled', 'studentfinaid', 'student_profile', 'class_approved', 'lotteried_students',  'teacher_profile', 'class_proposed', 'volunteer_all']

    def __init__(self, *args, **kwargs):
        self.updated = False

    def filter_from_criteria(self, base_list, criteria, program=None):
        return base_list.filter(self.query_from_criteria('any', criteria, program)).distinct()

    def query_from_criteria(self, user_type, criteria, program=None):

        """ Get the "base list" consisting of all the users of a specific type. """
        if user_type.lower() == 'any':
            Q_base = Q()
        else:
            if user_type not in ESPUser.getTypes():
                raise ESPError('user_type must be one of '+str(ESPUser.getTypes()))
            Q_base = ESPUser.getAllOfType(user_type, True)

        Q_include = Q()
        Q_exclude = Q()

        """ Apply the specified criteria to filter the list of users. """
        if criteria.get('userid', '').strip():

            ##  Select users based on their IDs only
            userid = []
            for digit in criteria['userid'].split(','):
                try:
                    userid.append(int(digit))
                except:
                    raise ESPError('User id invalid, please enter a number or comma-separated list of numbers.', log=False)

            if 'userid__not' in criteria:
                Q_exclude |= Q(id__in = userid)
            else:
                Q_include &= Q(id__in = userid)
            self.updated = True

        else:

            ##  Select users based on all other criteria that was entered
            if criteria.get('clsid', '').strip():
                clsid = []
                for digit in criteria['clsid'].split(','):
                    try:
                        clsid.append(int(digit))
                    except:
                        raise ESPError('Class id invalid, please enter a comma-separated list of numbers.', log=False)
                if 'regtypes' in criteria:
                    student_verbs = criteria['regtypes']
                else:
                    student_verbs = ['Enrolled']
                Q_include &= Q(studentregistration__section__parent_class__id__in=clsid,
                               studentregistration__relationship__name__in=student_verbs) & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')

            if 'class_times' in criteria:
                class_times = criteria['class_times']
                if 'regtypes' in criteria:
                    student_verbs = criteria['regtypes']
                else:
                    student_verbs = ['Enrolled']
                Q_include &= Q(studentregistration__section__meeting_times__id__in=class_times, studentregistration__relationship__name__in=student_verbs) \
                             & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')
                self.updated = True

            if 'teaching_times' in criteria:
                teaching_times = criteria['teaching_times']
                Q_include &= Q(classsubject__sections__meeting_times__id__in=teaching_times)
                self.updated = True

            if 'teacher_events' in criteria:
                teacher_events = criteria['teacher_events']
                Q_include &= Q(useravailability__event__id__in=teacher_events)
                self.updated = True

            if 'groups_include' in criteria:
                groups_include = criteria['groups_include']
                #Can't just filter by group because we are already filtering by group with user_type above. - willgearty, 2016-11-23
                Q_include &= Q(registrationprofile__user__groups__id__in=groups_include)
                self.updated = True

            if 'groups_exclude' in criteria:
                groups_exclude = criteria['groups_exclude']
                #Can't just filter by group because we are already filtering by group with user_type above. - willgearty, 2016-11-23
                Q_exclude |= Q(registrationprofile__user__groups__id__in=groups_exclude)
                self.updated = True

            for field in ['username','last_name','first_name', 'email']:
                if criteria.get(field, '').strip():
                    #   Check that it's a valid regular expression
                    try:
                        rc = re.compile(criteria[field])
                    except:
                        raise ESPError('Invalid search expression, please check your syntax: %s' % criteria[field], log=False)
                    filter_dict = {'%s__iregex' % field: criteria[field]}
                    if '%s__not' % field in criteria:
                        Q_exclude |= Q(**filter_dict)
                    else:
                        Q_include &= Q(**filter_dict)
                    self.updated = True

            if 'zipcode' in criteria and 'zipdistance' in criteria and \
                len(criteria['zipcode'].strip()) > 0 and len(criteria['zipdistance'].strip()) > 0:
                try:
                    zipc = ZipCode.objects.get(zip_code = criteria['zipcode'])
                except:
                    raise ESPError('Zip code not found.  This may be because you didn\'t enter a valid US zipcode.  Tried: "%s"' % criteria['zipcode'], log=False)
                zipcodes = zipc.close_zipcodes(criteria['zipdistance'])
                # Excludes zipcodes within a certain radius, giving an annulus; can fail to exclude people who used to live outside the radius.
                # This may have something to do with the Q_include line below taking more than just the most recent profile. -ageng, 2008-01-15
                if criteria.get('zipdistance_exclude', '').strip():
                    zipcodes_exclude = zipc.close_zipcodes(criteria['zipdistance_exclude'])
                    zipcodes = [ zipcode for zipcode in zipcodes if zipcode not in zipcodes_exclude ]
                if len(zipcodes) > 0:
                    Q_include &= Q(registrationprofile__contact_user__address_zip__in = zipcodes, registrationprofile__most_recent_profile=True)
                    self.updated = True

            if criteria.get('states', '').strip():
                state_codes = criteria['states'].strip().upper().split(',')
                if 'states__not' in criteria:
                    Q_exclude |= Q(registrationprofile__contact_user__address_state__in = state_codes, registrationprofile__most_recent_profile=True)
                else:
                    Q_include &= Q(registrationprofile__contact_user__address_state__in = state_codes, registrationprofile__most_recent_profile=True)
                self.updated = True

            if 'grade_min' in criteria:
                yog = ESPUser.YOGFromGrade(criteria['grade_min'])
                if yog != 0:
                    Q_include &= Q(registrationprofile__student_info__graduation_year__lte = yog, registrationprofile__most_recent_profile=True)
                    self.updated = True

            if 'grade_max' in criteria:
                yog = ESPUser.YOGFromGrade(criteria['grade_max'])
                if yog != 0:
                    Q_include &= Q(registrationprofile__student_info__graduation_year__gte = yog, registrationprofile__most_recent_profile=True)
                    self.updated = True

            if 'school' in criteria:
                school = criteria['school']
                if school:
                    Q_include &= (Q(studentinfo__school__icontains=school) | Q(studentinfo__k12school__name__icontains=school))
                    self.updated = True

            #   Filter by graduation years if specifically looking for teachers.
            possible_gradyears = range(1920, 2120)
            if criteria.get('gradyear_min', '').strip():
                try:
                    gradyear_min = int(criteria['gradyear_min'])
                except:
                    raise ESPError('Please enter a 4-digit integer for graduation year limits.', log=False)
                possible_gradyears = filter(lambda x: x >= gradyear_min, possible_gradyears)
            if criteria.get('gradyear_max', '').strip():
                try:
                    gradyear_max = int(criteria['gradyear_max'])
                except:
                    raise ESPError('Please enter a 4-digit integer for graduation year limits.', log=False)
                possible_gradyears = filter(lambda x: x <= gradyear_max, possible_gradyears)
            if criteria.get('gradyear_min', None) or criteria.get('gradyear_max', None):
                Q_include &= Q(registrationprofile__teacher_info__graduation_year__in = map(str, possible_gradyears), registrationprofile__most_recent_profile=True)
                self.updated = True

            if 'hours_min' in criteria or 'hours_max' in criteria:
                current_Q = Q_base & (Q_include & ~Q_exclude)
                user_hours = {user.id: (sum([section.meeting_times.count() for section in user.getEnrolledSections(program)])) for user in ESPUser.objects.filter(current_Q)}
                exclude_user_list = []
                if 'hours_min' in criteria:
                    hours_min = criteria['hours_min']
                    if hours_min:
                        for user, hours in user_hours.items():
                            if hours < int(hours_min):
                                exclude_user_list.append(user)
                if 'hours_max' in criteria:
                    hours_max = criteria['hours_max']
                    if hours_max:
                        for user, hours in user_hours.items():
                            if hours > int(hours_max):
                                exclude_user_list.append(user)
                Q_exclude |= Q(id__in=exclude_user_list)
                self.updated = True

            if 'target_user' in criteria:
                student_id = criteria['target_user']
                if student_id == "invalid":
                    raise ESPError('Please select a valid student whose teachers to email.', log=False)
                else:
                    sections = [sr.section for sr in StudentRegistration.valid_objects().filter(user_id=student_id, relationship__name="Enrolled", section__parent_class__parent_program=program)]
                    if len(sections):
                        teacher_filter = Q(classsubject__sections__in=sections)
                    else:
                        teacher_filter = Q(classsubject__sections__in=sections)
                    Q_include &= teacher_filter
                    self.updated = True
        return Q_base & (Q_include & ~Q_exclude)

    def query_from_postdata(self, program, data):
        """ Get a Q object for the targeted list of users from the POST data submitted
            on the main "comm panel" page
        """

        def get_recipient_type(list_name):
            for user_type in Program.USER_TYPE_LIST_FUNCS:
                raw_lists = getattr(program, user_type)(True)
                if list_name in raw_lists:
                    return user_type

        subquery = None

        if 'base_list' in data and 'recipient_type' in data:
            #   Get the program-specific part of the query (e.g. which list to use)
            if data['recipient_type'] not in ESPUser.getTypes():
                recipient_type = 'any'
                q_program = Q()
            else:
                if data['base_list'].startswith('all'):
                    q_program = Q()
                    recipient_type = data['recipient_type']
                else:
                    program_lists = getattr(program, data['recipient_type'].lower()+'s')(QObjects=True)
                    q_program = program_lists[data['base_list']]
                    """ Some program queries rely on UserBits, and since user types are also stored in
                        UserBits we cannot store both of these in a single Q object.  To compensate, we
                        ignore the user type when performing a program-specific query.  """
                    recipient_type = 'any'

            #   Get the user-specific part of the query (e.g. ID, name, school)
            q_extra = self.query_from_criteria(recipient_type, data, program)

        ##  Handle "combination list" submissions
        elif 'combo_base_list' in data:
            #   Get an initial query from the supplied base list
            recipient_type, list_name = data['combo_base_list'].split(':')
            if list_name.startswith('all'):
                q_program = Q()
            else:
                q_program = getattr(program, recipient_type.lower()+'s')(QObjects=True)[list_name]

            #   Apply Boolean filters
            #   Base list will be intersected with any lists marked 'AND', and then unioned
            #   with any lists marked 'OR'.
            checkbox_keys = map(lambda x: x[9:], filter(lambda x: x.startswith('checkbox_'), data.keys()))
            and_keys = map(lambda x: x[4:], filter(lambda x: x.startswith('and_'), checkbox_keys))
            or_keys = map(lambda x: x[3:], filter(lambda x: x.startswith('or_'), checkbox_keys))
            not_keys = map(lambda x: x[4:], filter(lambda x: x.startswith('not_'), checkbox_keys))
            #if any keys concern the same field, we will place them into
            #a subquery and count occurrences

            #for the purpose of experimentation simply fix this to the record__event
            #as this could very well have different implications for other fields

            subqry_fieldmap = {'record__event':[]}

            for and_list_name in and_keys:
                user_type = get_recipient_type(and_list_name)

                if user_type:

                    qobject = getattr(program, user_type)(QObjects=True)[and_list_name]

                    if and_list_name in not_keys:
                        q_program = q_program & ~qobject
                    else:
                        qobject_child = qobject.children[1]
                        needs_subquery = False

                        if isinstance(qobject_child, (list, tuple)):
                            field_name, field_value = qobject.children[1]
                            needs_subquery = field_name in subqry_fieldmap

                            if needs_subquery:
                                subqry_fieldmap[field_name].append(field_value)
                        if not needs_subquery:
                            q_program = q_program & qobject

            event_fields = subqry_fieldmap['record__event']

            if event_fields:
                #annotation is needed to initiate group by
                #except that it causes the query to return two columns
                #so we call values at the end of the chain, however,
                #that results in multiple group by fields(causing the query to fail)
                #so, we assign a group by field, to force grouping by user_id
                subquery = (
                              Record
                              .objects
                              .filter(program=program,event__in=event_fields)
                              .annotate(numusers=Count('user__id'))
                              .filter(numusers=len(event_fields))
                              .values_list('user_id',flat=True)
                            )

                subquery.query.group_by = []#leave empty to strip out duplicate group by
                subquery = Q(pk__in=subquery)

            for or_list_name in or_keys:
                user_type = get_recipient_type(or_list_name)
                if user_type:
                    qobject = getattr(program, user_type)(QObjects=True)[or_list_name]
                    if or_list_name not in not_keys:
                        q_program = q_program | qobject
                    else:
                        q_program = q_program | ~qobject

            #   Get the user-specific part of the query (e.g. ID, name, school)
            q_extra = self.query_from_criteria(recipient_type, data, program)

        qobject = (q_extra & q_program & Q(is_active=True))

        #strip out duplicate clauses
        #   Note: in some cases, the children of the Q object are unhashable.
        #   Keep these separate.
        clauses_hashable = []
        clauses_unhashable = []
        for clause in qobject.children:
            if isinstance(clause, Q) or (isinstance(clause, tuple) and isinstance(clause[1], collections.Hashable)):
                clauses_hashable.append(clause)
            else:
                clauses_unhashable.append(clause)
        qobject.children = list(set(clauses_hashable)) + clauses_unhashable

        if subquery:
            qobject = qobject & subquery
        return qobject

    def filter_from_postdata(self, program, data):
        """ Wraps the query_from_postdata function above to return a PersistentQueryFilter. """

        query = self.query_from_postdata(program, data)

        #TODO-determine best location to inject subquery
        #the string subquery should be assigned to .extra of the resultant filter
        filterObj = PersistentQueryFilter.create_from_Q(ESPUser, query)

        if 'base_list' in data and 'recipient_type' in data:
            filterObj.useful_name = 'Program list: %s' % data['base_list']
        elif 'combo_base_list' in data:
            filterObj.useful_name = 'Custom user list'
        filterObj.save()
        return filterObj

    def sendto_fn_from_postdata(self, data):
        recipient_type = data.get('recipient_type', '') or data.get('combo_base_list', ':').split(':')[0]
        sendtos = []
        if recipient_type == 'Student':
            for key,value in data.iteritems():
                if ('student_sendto_' in key) and (value == '1'):
                    sendtos.append(key[1+key.rindex('_'):])
            if not sendtos:
                sendtos.append('self')
            sendtos.sort(key=['self', 'guardian', 'emergency'].index)
            return 'send_to_' + '_and_'.join(sendtos)
        else:
            return MessageRequest.SEND_TO_SELF_REAL

    def prepare_context(self, program, target_path=None):
        context = {}
        context['program'] = program
        context['user_types'] = ESPUser.getTypes()
        category_lists = {}
        list_descriptions = program.getListDescriptions()

        #   Add in program-specific lists for most common user types
        for user_type, list_func in zip(Program.USER_TYPES_WITH_LIST_FUNCS, Program.USER_TYPE_LIST_FUNCS):
            raw_lists = getattr(program, list_func)(True)
            category_lists[user_type] = [{'name': key, 'list': raw_lists[key], 'description': list_descriptions[key]} for key in raw_lists]
            for item in category_lists[user_type]:
                if item['name'] in UserSearchController.preferred_lists:
                    item['preferred'] = True

        #   Add in global lists for each user type
        for user_type in ESPUser.getTypes():
            key = user_type.lower() + 's'
            if user_type not in category_lists:
                category_lists[user_type] = []
            category_lists[user_type].insert(0, {'name': 'all_%s' % user_type, 'list': ESPUser.getAllOfType(user_type), 'description': 'All %s in the database' % key, 'preferred': True, 'all_flag': True})

        #   Add in mailing list accounts
        category_lists['emaillist'] = [{'name': 'all_emaillist', 'list': Q(password = 'emailuser'), 'description': 'Everyone signed up for the mailing list', 'preferred': True}]

        context['lists'] = category_lists
        context['all_list_names'] = []
        for category in category_lists:
            for item in category_lists[category]:
                context['all_list_names'].append(item['name'])

        if target_path is None:
            target_path = '/manage/%s/commpanel' % program.getUrlBase()
        context['action_path'] = target_path
        context['groups'] = Group.objects.all()
        context['regtypes'] = RegistrationType.objects.all().order_by("name")
        context['class_times'] = program.getTimeSlots(types = [EventType.get_from_desc('Class Time Block')]).order_by('start')
        context['teacher_events'] = program.getTimeSlots(types = [EventType.get_from_desc('Teacher Training'), EventType.get_from_desc('Teacher Interview')]).order_by('start')

        return context

    def create_filter(self, request, program, template=None, target_path=None):
        """ Function to obtain a list of users, possibly requiring multiple requests.
            Similar to the old get_user_list function.
        """

        if template is None:
            template = 'users/usersearch/usersearch_default.html'

        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = {}
            for key in request.POST:
                data[key] = request.POST[key]

            #   Look for signs that this request contains user search options and act accordingly
            if ('base_list' in data and 'recipient_type' in data) or ('combo_base_list' in data):
                filterObj = self.filter_from_postdata(program, data)
                return (filterObj, True)

        if target_path is None:
            target_path = request.path

        return (render_to_response(template, request, self.prepare_context(program, target_path)), False)

    def selected_list_from_postdata(self, data):
        selected = []
        selected.append(str(data.get('base_list', '')) or str(data.get('combo_base_list', ':').split(':')[1]))
        for k,v in data.items():
            if k.startswith('checkbox_'):
                selected.append(str(k.split('checkbox_')[1]))

        return str(', '.join(selected))
