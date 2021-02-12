
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
  Email: web-team@learningu.org
"""

from esp.program.modules.base import ProgramModuleObj, needs_student, main_call
from esp.utils.web import render_to_response

from esp.program.modules.forms.splashinfo import SplashInfoForm
from esp.program.models import SplashInfo
from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from django.db.models.query import Q

class SplashInfoModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
      return {
          "link_title": "Lunch Preferences & Sibling Discount",
          "module_type": "learn",
          "seq": 20,
          "required": True,
          "choosable": 2,
          }

    def students(self, QObject=False):
        Q_students = Q(splashinfo__program = self.program)

        result = {}
        result['siblingdiscount'] = Q_students & Q(splashinfo__siblingdiscount=True)

        for val in SplashInfo.objects.values_list('lunchsat').distinct():
            if val[0] is not None:
                result['lunchsat_'+val[0]] = Q_students & Q(splashinfo__lunchsat=val[0])

        for val in SplashInfo.objects.values_list('lunchsun').distinct():
            if val[0] is not None:
                result['lunchsun_'+val[0]] = Q_students & Q(splashinfo__lunchsun=val[0])

        if QObject:
            return result
        else:
            for key in result:
                result[key] = ESPUser.objects.filter(result[key])
            return result

    def studentDesc(self):
        result = {}
        result['siblingdiscount'] = """Students who have a sibling discount"""

        for val in SplashInfo.objects.values_list('lunchsat').distinct():
            if val[0] is not None:
                result['lunchsat_'+val[0]] = """Students who selected {0} for lunch on Saturday""".format(val[0])
        for val in SplashInfo.objects.values_list('lunchsun').distinct():
            if val[0] is not None:
                result['lunchsun_'+val[0]] = """Students who selected {0} for lunch on Sunday""".format(val[0])

        return result


    def isCompleted(self):
        return SplashInfo.hasForUser(get_current_request().user, self.program)

    def isStep(self):
        return True

    def prepare(self, context={}):
        context['splashinfo'] = SplashInfo.getForUser(get_current_request().user, self.program)
        context['splashinfo'].include_siblingdiscount = Tag.getBooleanTag('splashinfo_siblingdiscount', program=self.program)
        context['splashinfo'].include_lunchsat = Tag.getBooleanTag('splashinfo_lunchsat', program=self.program)
        context['splashinfo'].include_lunchsun = Tag.getBooleanTag('splashinfo_lunchsun', program=self.program)

        return context

    @main_call
    @needs_student
    def splashinfo(self, request, tl, one, two, module, extra, prog):
        form = SplashInfoForm(program=prog)

        missing_siblingname = False
        if request.method == 'POST':
            new_data = request.POST.copy()
            form = SplashInfoForm(new_data, program=prog)
            if form.is_valid():
                if 'siblingdiscount' in form.cleaned_data and eval(form.cleaned_data['siblingdiscount']) and len(form.cleaned_data['siblingname']) == 0:
                    missing_siblingname = True
                else:
                    spi = SplashInfo.getForUser(request.user, self.program)
                    form.save(spi)
                    return self.goToCore(tl)
        else:
            spi = SplashInfo.getForUser(request.user, self.program)
            form.load(spi)

        context = {}
        context['form'] = form
        context['missing_siblingname'] = missing_siblingname

        return render_to_response(self.baseDir()+'splashinfo.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
