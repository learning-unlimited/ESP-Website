
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

import json
from esp.tagdict.models import Tag
from esp.program.models import RegistrationType, Program

class RegistrationTypeController(object):

    key = 'display_registration_names'
    default_names = ["Enrolled",]
    default_rts = RegistrationType.objects.filter(name__in=default_names).distinct()

    @classmethod
    def getVisibleRegistrationTypeNames(cls, prog, for_VRT_form = False):
        if not (prog and isinstance(prog,(Program,int))):
            return set(cls.default_names)
        if isinstance(prog,int):
            try:
                prog = Program.objects.get(pk=prog)
            except Exception:
                return set(cls.default_names)
        display_names = Tag.getProgramTag(key=cls.key, program=prog)
        if display_names:
            display_names = json.loads(display_names) + cls.default_names
        else:
            display_names = cls.default_names
        if "All" in display_names:
            display_names = list(RegistrationType.objects.all().values_list('name',flat=True).distinct().order_by('name'))
            if for_VRT_form:
                display_names.append("All")
        return display_names

    @classmethod
    def setVisibleRegistrationTypeNames(cls, display_names, prog):
        if not (prog and isinstance(prog,(Program,int))):
            return False
        if isinstance(prog,int):
            try:
                prog = Program.objects.get(pk=prog)
            except Exception:
                return False
        try:
            if "All" in display_names:
                display_names = cls.default_names + ["All"]
            Tag.setTag(key=cls.key, target=prog, value=json.dumps(display_names))
            return True
        except Exception:
            return False
