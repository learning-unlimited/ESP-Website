
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
  Email: web-team@learningu.org
"""

from esp.utils.web import render_to_response
from esp.users.models import PersistentQueryFilter, K12School, ContactInfo, ESPUser, User, ESPError, ZipCode
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_grade, main_call, aux_call
from esp.program.modules import module_ext
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q
from esp.program.modules.forms.mailinglabels_schools import SchoolSelectForm
from esp.program.modules.forms.mailinglabels_banzips import BanZipsForm
import operator



class MailingLabels(ProgramModuleObj):
    """ This allows one to generate Mailing Labels for both schools and users. You have the option of either creating a file which can be sent to MIT mailing services or actually create printable files.
    """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Mailing Label Generation",
            "link_title": "Generate Mailing Labels",
            "module_type": "manage",
            "seq": 100,
            "choosable": 1,
            }

    @aux_call
    @needs_admin
    def badzips(self, request, tl, one, two, module, extra, prog):
        """ This function will allow someone to enter zip codes to mark as undeliverable. """
        if request.method=="POST":
            form = BanZipsForm(request.POST)
            if form.is_valid():
                zips = form.cleaned_data['zips'].strip().splitlines()
                for zipc in zips:
                    if len(zipc.strip()) < 10:
                        continue
                    for c in ContactInfo.objects.filter(address_postal__contains = "'%s'" % zipc.strip()):
                        c.undeliverable = True
                        c.save()
                return HttpResponseRedirect("/%s/%s/%s/mailinglabel/" % (tl, one, two))

        else:
            form = BanZipsForm()

        return render_to_response(self.baseDir()+"mailinglabel_badzips.html", request, {'form': form})


    @main_call
    @needs_admin
    def mailinglabel(self, request, tl, one, two, module, extra, prog):
        """ This function will allow someone to generate mailing labels. """
        from esp.users.views     import get_user_list

        combine = True

        if extra is None or extra.strip() == '':
            return render_to_response(self.baseDir()+'mailinglabel_index.html',request, {})

        if 'nocombine' in extra.strip().lower():
            combine = False

        if 'schools' in extra.strip():
            if request.method == 'POST':

                if 'filter_id' in request.POST:
                    """
                    A filter was passed.
                    """
                    f = PersistentQueryFilter.objects.get(id = request.POST['filter_id'])
                    combine = (request.POST['combine'].upper() in ('TRUE','1','T'))
                    infos = f.getList(ContactInfo).distinct()
                else:

                    form = SchoolSelectForm(request.POST)
                    if form.is_valid():
                        try:
                            zipc = ZipCode.objects.get(zip_code = form.cleaned_data['zip_code'])
                        except:
                            raise ESPError('Please enter a valid US zipcode. "%s" is not valid.' % form.cleaned_data['zip_code'], log=False)

                        zipcodes = zipc.close_zipcodes(form.cleaned_data['proximity'])

                        combine = form.cleaned_data['combine_addresses']

                        Q_infos = Q(k12school__id__isnull = False,
                                    address_zip__in = zipcodes)

                        grades = form.cleaned_data['grades'].strip().split(',')
                        if len(form.cleaned_data['grades_exclude'].strip()) == 0:
                            grades_exclude = []
                        else:
                            grades_exclude = form.cleaned_data['grades_exclude'].strip().split(',')

                        if len(grades) > 0:
                            Q_grade = reduce(operator.or_, [Q(k12school__grades__contains = grade) for grade in grades])
                            Q_infos &= Q_grade

                        if len(grades_exclude) > 0:
                            Q_grade = reduce(operator.or_, [Q(k12school__grades__contains = grade) for grade in grades_exclude])
                            Q_infos &= ~Q_grade

                        f = PersistentQueryFilter.create_from_Q(ContactInfo, Q_infos, description="All ContactInfos for K12 schools with grades %s and %s miles from zipcode %s." % (form.cleaned_data['grades'], form.cleaned_data['proximity'], form.cleaned_data['zip_code']))

                        num_schools = ContactInfo.objects.filter(Q_infos).distinct().count()

                        return render_to_response(self.baseDir()+'schools_confirm.html', request, {'filter':f,'num': num_schools, 'combine': combine})

                    else:
                        return render_to_response(self.baseDir()+'selectschools.html', request, {'form': form})

            else:
                form = SchoolSelectForm(initial = {'zip_code': '02139',
                                                   'combine_addresses': True})

                return render_to_response(self.baseDir()+'selectschools.html', request, {'form': form})

        else:
            filterObj, found = get_user_list(request, self.program.getLists(True))

            if not found:
                return filterObj

            infos = [user.getLastProfile().contact_user for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]

            infos_filtered = [ info for info in infos if (info != None and info.undeliverable != True) ]

        output = MailingLabels.gen_addresses(infos, combine)

        if 'csv' in extra.strip():
            response = HttpResponse('\n'.join(output), content_type = 'text/plain')
            return response


    @staticmethod
    def gen_addresses(infos, combine = True):
        """ Takes a iterable list of infos and returns a lits of addresses. """

        import pycurl
        from django.template.defaultfilters import urlencode
        import re
        import time


        regex = re.compile(r""""background:url\(images\/table_gray.gif\); padding\:5px 10px;">\s*(.*?)<br \/>\s*(.*?)&nbsp;(.{2})&nbsp;&nbsp;(\d{5}\-\d{4})""")


        addresses = {}
        ids_zipped = []

        infos = [i for i in infos if i != None]

        if len(infos) > 0 and infos[0].k12school_set.all().count() > 0:
            use_title = True
        else:
            use_title = False

        for info in infos:
            if info == None:
                continue

            schools = info.k12school_set.all()

            if len(schools) > 0:
                if schools[0].contact_title == 'SCHOOL':
                    title = None
                else:
                    title = schools[0].contact_title
            else:
                title = None

            if use_title:
                name = "'%s %s','%s'" % (info.first_name.strip(), info.last_name.strip(), title)
            else:
                name = '%s %s' % (info.first_name.strip(), info.last_name.strip())

            if info.address_postal != None:
                key = info.address_postal
            else:

                ids_zipped.append(info.id)

                post_data =  {'visited' : 1,
                              'pagenumber': 0,
                              'firmname': '',
                              'address1': '',
                              'urbanization': '',
                              'submit_x' : '',
                              'submit_y' : '',
                              'submit':    'Find ZIP Code'}


                post_data.update({'address2': info.address_street.title(),
                                  'state'   : info.address_state,
                                  'city'    : info.address_city.title(),
                                  'zip5'    : info.address_zip,
                                  })

                post_string = '&'.join(['%s=%s' % (key, urlencode(value)) for key, value in post_data.iteritems()])

                c = pycurl.Curl()

                c.setopt(pycurl.URL, 'http://zip4.usps.com/zip4/zcl_0_results.jsp')
                c.setopt(pycurl.POSTFIELDS, post_string)
                c.setopt(pycurl.POST, 1)
                c.setopt(pycurl.REFERER, 'http://zip4.usps.com/zip4/welcome.jsp')
                #c.setopt(pycurl.RETURNTRANSFER, True)



                import StringIO
                b = StringIO.StringIO()
                c.setopt(pycurl.WRITEFUNCTION, b.write)

                c.perform()

                retdata = b.getvalue().replace('\n','').replace('\r','')

                ma = regex.search(retdata)
                try:
                    key = "'%s','%s','%s','%s'" % (ma.group(1),
                                                   ma.group(2),
                                                   ma.group(3),
                                                   ma.group(4))
                    info.address_postal = key
                except:
                    key = False
                    info.address_postal = 'FAILED'

                info.save()

            if key != 'FAILED':

                if key in addresses:
                    if name.upper() not in [n.upper() for n in addresses[key]]:
                        addresses[key].append(name)
                else:
                    addresses[key] = [name]


                #time.sleep(1)
        if use_title:
            output = ["'Num','Name','Title','Street','City','State','Zip'"]
        else:
            output = ["'Num','Name','Street','City','State','Zip'"]
        #output.append(','.join(ids_zipped))
        i = 1
        for key, value in addresses.iteritems():
            if key != False:
                if combine:
                    if use_title:
                        output.append("'%s',%s,%s" % (i, ' and '.join(value), key))
                    else:
                        output.append("'%s','%s',%s" % (i,' and '.join(value), key))
                    i += 1
                else:
                    for name in value:
                        if use_title:
                            output.append("'%s',%s,%s" % (i, name, key))
                        else:
                            output.append("'%s','%s',%s" % (i, name, key))
                        i += 1

        return output




    class Meta:
        proxy = True
        app_label = 'modules'
