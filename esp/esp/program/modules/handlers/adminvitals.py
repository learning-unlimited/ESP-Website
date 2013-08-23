
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.program.models import ClassSubject, ClassSection, Program, ClassCategories
from esp.program.models.class_ import open_class_category
from esp.users.models import ESPUser, shirt_sizes, shirt_types
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.query      import Q
from collections import defaultdict
import math
from decimal import Decimal

class KeyDoesNotExist(Exception):
    pass

class AdminVitals(ProgramModuleObj):
    doc = """ This allows you to view the major numbers for your program on the main page.
        This will present itself below the options in a neat little table. """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Admin Module for Showing Basic Vitals",
            "link_title": "Program Vitals",
            "module_type": "manage",
            "inline_template": "vitals.html",
            "seq": -2,
            }
    
    def prepare(self, context=None):
        return context



    class Meta:
        abstract = True

