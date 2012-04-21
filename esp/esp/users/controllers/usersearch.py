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
  Email: web-team@lists.learningu.org
"""

from esp.users.models import ESPUser
from esp.middleware import ESPError

from django.db.models.query import Q

import re

class UserSearchController(object):
    def __init__(self, *args, **kwargs):
        self.updated = False

    def filter_from_criteria(self, base_list, criteria):
        return base_list.filter(self.query_from_criteria('any', criteria)).distinct()

    def query_from_criteria(self, user_type, criteria):
    
        """ Get the "base list" consisting of all the users of a specific type. """
        if user_type.lower() == 'any':
            Q_base = Q()
        else:
            if user_type not in ESPUser.getTypes():
                raise ESPUser(), 'user_type must be one of '+str(ESPUser.getTypes())
            Q_base = ESPUser.getAllOfType(user_type, True)
            
        Q_include = Q()
        Q_exclude = Q()

        """ Apply the specified criteria to filter the list of users. """
        if criteria.has_key('userid') and len(criteria['userid'].strip()) > 0:
        
            ##  Select users based on their IDs only
            userid = []
            for digit in criteria['userid'].split(','):
                try:
                    userid.append(int(digit))
                except:
                    raise ESPError(False), 'User id invalid, please enter a number or comma-separated list of numbers.'
                    
            if criteria.has_key('userid__not'):
                Q_exclude &= Q(id__in = userid)
            else:
                Q_include &= Q(id__in = userid)
            self.updated = True
                
        else:
        
            ##  Select users based on all other criteria that was entered
            for field in ['username','last_name','first_name', 'email']:
                if criteria.has_key(field) and len(criteria[field].strip()) > 0:
                    #   Check that it's a valid regular expression
                    try:
                        rc = re.compile(criteria[field])
                    except:
                        raise ESPError(False), 'Invalid search expression, please check your syntax: %s' % criteria[field]
                    filter_dict = {'%s__iregex' % field: criteria[field]}
                    if criteria.has_key('%s__not' % field):
                        Q_exclude &= Q(**filter_dict)
                    else:
                        Q_include &= Q(**filter_dict)
                    self.updated = True

            if criteria.has_key('zipcode') and criteria.has_key('zipdistance') and \
                len(criteria['zipcode'].strip()) > 0 and len(criteria['zipdistance'].strip()) > 0:
                try:
                    zipc = ZipCode.objects.get(zip_code = criteria['zipcode'])
                except:
                    raise ESPError(False), 'Please enter a valid US zipcode.'
                zipcodes = zipc.close_zipcodes(criteria['zipdistance'])
                # Excludes zipcodes within a certain radius, giving an annulus; can fail to exclude people who used to live outside the radius.
                # This may have something to do with the Q_include line below taking more than just the most recent profile. -ageng, 2008-01-15
                if criteria.has_key('zipdistance_exclude') and len(criteria['zipdistance_exclude'].strip()) > 0:
                    zipcodes_exclude = zipc.close_zipcodes(criteria['zipdistance_exclude'])
                    zipcodes = [ zipcode for zipcode in zipcodes if zipcode not in zipcodes_exclude ]
                if len(zipcodes) > 0:
                    Q_include &= Q(registrationprofile__contact_user__address_zip__in = zipcodes, registrationprofile__most_recent_profile=True)
                    self.updated = True

            if criteria.has_key('states') and len(criteria['states'].strip()) > 0:
                state_codes = criteria['states'].strip().upper().split(',')
                if criteria.has_key('states__not'):
                    Q_exclude &= Q(registrationprofile__contact_user__address_state__in = state_codes, registrationprofile__most_recent_profile=True)
                else:
                    Q_include &= Q(registrationprofile__contact_user__address_state__in = state_codes, registrationprofile__most_recent_profile=True)
                self.updated = True

            if criteria.has_key('grade_min'):
                yog = ESPUser.YOGFromGrade(criteria['grade_min'])
                if yog != 0:
                    Q_include &= Q(registrationprofile__student_info__graduation_year__lte = yog, registrationprofile__most_recent_profile=True)
                    self.updated = True

            if criteria.has_key('grade_max'):
                yog = ESPUser.YOGFromGrade(criteria['grade_max'])
                if yog != 0:                
                    Q_include &= Q(registrationprofile__student_info__graduation_year__gte = yog, registrationprofile__most_recent_profile=True)
                    self.updated = True
        
            if criteria.has_key('school'):
                school = criteria['school']
                if school:
                    Q_include &= (Q(studentinfo__school__icontains=school) | Q(studentinfo__k12school__name__icontains=school))
                    self.updated = True
        
            #   Filter by graduation years if specifically looking for teachers.
            possible_gradyears = range(1920, 2020)
            if criteria.has_key('gradyear_min') and len(criteria['gradyear_min'].strip()) > 0:
                try:
                    gradyear_min = int(criteria['gradyear_min'])
                except:
                    raise ESPError(False), 'Please enter a 4-digit integer for graduation year limits.'
                possible_gradyears = filter(lambda x: x >= gradyear_min, possible_gradyears)
            if criteria.has_key('gradyear_max') and len(criteria['gradyear_min'].strip()) > 0:
                try:
                    gradyear_max = int(criteria['gradyear_max'])
                except:
                    raise ESPError(False), 'Please enter a 4-digit integer for graduation year limits.'
                possible_gradyears = filter(lambda x: x <= gradyear_max, possible_gradyears)
            if criteria.get('gradyear_min', None) or criteria.get('gradyear_max', None):
                Q_include &= Q(registrationprofile__teacher_info__graduation_year__in = map(str, possible_gradyears), registrationprofile__most_recent_profile=True)
                self.updated = True
                
        return Q_base & (Q_include & ~Q_exclude)
        
