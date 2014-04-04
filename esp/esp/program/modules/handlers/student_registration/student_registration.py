
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

import simplejson

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.core.cache import cache
from django.db.models.query import Q, QuerySet
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_cookie

from esp.cache           import cache_function
from esp.cal.models import Event, EventType
from esp.datatree.models import *
from esp.middleware      import ESPError, AjaxError, ESPError_Log, ESPError_NoLog
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.models  import ClassSubject, ClassSection, ClassCategories, RegistrationProfile, ClassImplication, StudentRegistration
from esp.program.modules import module_ext
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.program.templatetags.class_render import render_class_direct
from esp.tagdict.models  import Tag
from esp.users.models    import ESPUser, Permission, Record
from esp.utils.no_autocookie import disable_csrf_cookie_update
from esp.utils.query_utils import nest_Q
from esp.web.util        import render_to_response

from abc import ABCMeta, abstractmethod

class StudentRegistrationMixin(object):

    def students(self):
        raise NotImplementedError

    def studentDesc(self):
        raise NotImplementedError

    def isCompleted(self):
        raise NotImplementedError

    def _group_columns(self, items):
            # collect into groups of 5
        cols = []
        for i, item in enumerate(items):
            if i % 5 == 0:
                col = []
                cols.append(col)
            col.append(item)
        return cols

    def base_dir(self):
        base_dir = 'program/modules/student_registration/'
        return base_dir

    def catalog_context(self, request, tl, one, two, module, extra, prog):
        """
        Builds context specific to the catalog. Used by all views which render
        the catalog. This is not a view in itself.
        """
        context = {}
        # FIXME(gkanwar): This is a terrible hack, we should find a better way
        # to filter out certain categories of classes
        context['open_class_category_id'] = prog.open_class_category.id
        context['lunch_category_id'] = ClassCategories.objects.get(category='Lunch').id

        return context

    def get_class_context(self, request, tl, one, two, module, extra, prog):
        category_choices = []
        for category in prog.class_categories.all():
            # FIXME(gkanwar): Make this less hacky, once #770 is resolved
            if category.category == 'Lunch':
                continue
            category_choices.append((category.id, category.category))

        grade_choices = [('ALL', 'All')] + [(grade, grade) for grade in range(prog.grade_min, prog.grade_max + 1)]

        context = {}
        context['category_choices'] = self._group_columns(category_choices)
        context['grade_choices'] = self._group_columns(grade_choices)
        context.update(self.catalog_context(request, tl, one, two,module, extra, prog))

        return context

    @aux_call
    def view_classes(self, request, tl, one, two, module, extra, prog):
        """
        Displays a filterable catalog that anyone can view.
        """
        # get choices for filtering options
        class_context = self.get_class_context(request, tl, one, two, module, extra, prog)
        class_context['extra'] = extra
        return render_to_response('view_classes.html', request, class_context)





