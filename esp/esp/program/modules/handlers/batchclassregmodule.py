
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2024 by the individual contributors
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.utils.web import render_to_response
from esp.users.models import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from esp.program.models import ClassSection, ClassSubject
from esp.program.class_status import ClassStatus
from esp.middleware import ESPError

import logging
logger = logging.getLogger(__name__)


class BatchClassRegModule(ProgramModuleObj):
    doc = """Batch register a group of students to a class section."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Batch Class Registration",
            "link_title": "Batch Register Students to a Class",
            "module_type": "manage",
            "seq": 503,
            "choosable": 1,
        }

    @main_call
    @needs_admin
    def batchclassreg(self, request, tl, one, two, module, extra, prog):
        usc = UserSearchController()
        context = {}
        context['program'] = prog

        if request.method == "POST":
            data = ListGenModule.processPost(request)
            filterObj = UserSearchController().filter_from_postdata(prog, data)

            context['filterid'] = filterObj.id
            context['num_users'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            context['sections_by_subject'] = self.get_sections_for_program(prog)

            return render_to_response(self.baseDir()+'options.html', request, context)

        context.update(usc.prepare_context(prog, target_path='/manage/%s/batchclassreg' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    @aux_call
    @needs_admin
    def batchclassregfinal(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST' or 'filterid' not in request.GET:
            raise ESPError()('Filter and/or section has not been properly set')

        section_id = request.POST.get('section_id', '')
        if not section_id:
            raise ESPError()('No class section was selected')

        try:
            section = ClassSection.objects.get(
                id=int(section_id),
                parent_class__parent_program=prog
            )
        except (ClassSection.DoesNotExist, ValueError):
            raise ESPError()('Invalid class section selected')

        filterObj = PersistentQueryFilter.objects.get(id=request.GET['filterid'])
        override_full = 'override_full' in request.POST

        log = self.batch_register(filterObj, section, override_full)

        context = {
            'log': log,
            'section': section,
            'program': prog,
        }
        return render_to_response(self.baseDir()+'finished.html', request, context)

    @staticmethod
    def get_sections_for_program(prog):
        subjects = ClassSubject.objects.filter(
            parent_program=prog,
            status__gte=ClassStatus.ACCEPTED
        ).order_by('category__symbol', 'id').prefetch_related('sections')

        result = []
        for subject in subjects:
            section_list = []
            for section in subject.get_sections():
                if section.status >= ClassStatus.ACCEPTED:
                    try:
                        cap = section.capacity
                        is_full = section.isFull()
                    except Exception:
                        cap = section.max_class_capacity or 0
                        is_full = section.num_students() >= cap if cap else False
                    section_list.append({
                        'section': section,
                        'id': section.id,
                        'emailcode': section.emailcode(),
                        'title': section.title(),
                        'friendly_times': ', '.join(section.friendly_times()),
                        'num_students': section.num_students(),
                        'capacity': cap,
                        'is_full': is_full,
                        'rooms': ', '.join(section.prettyrooms()),
                    })
            if section_list:
                result.append({
                    'subject': subject,
                    'emailcode': subject.emailcode(),
                    'title': subject.title,
                    'sections': section_list,
                })
        return result

    @staticmethod
    def batch_register(filterobj, section, override_full=False):
        users = filterobj.getList(ESPUser)
        try:
            users = users.distinct()
        except:
            pass

        if not users:
            raise ESPError()("Your query did not match any users")

        log_lines = []
        log_lines.append(
            "Batch registering %d users for %s: %s" % (
                users.count(), section.emailcode(), section.title()
            )
        )
        log_lines.append(
            "Section capacity: %d, Current enrollment: %d, Override full: %s"
            % (section.capacity, section.num_students(), override_full)
        )
        log_lines.append("")

        program = section.parent_class.parent_program
        success_count = 0
        fail_count = 0
        skip_count = 0

        for user in users:
            already_enrolled = user.getEnrolledSections(program=program)
            already_in_section = any(
                s.id == section.id for s in already_enrolled
            )
            if already_in_section:
                log_lines.append(
                    "[SKIP] %s (ID %d): Already registered in this section"
                    % (user.name(), user.id)
                )
                skip_count += 1
                continue

            section_times = set(section.meeting_times.values_list('id', flat=True))
            conflict_sections = []
            for enrolled_sec in already_enrolled:
                enrolled_times = set(
                    enrolled_sec.meeting_times.values_list('id', flat=True)
                )
                if section_times & enrolled_times:
                    conflict_sections.append(enrolled_sec)

            if conflict_sections:
                conflict_names = ', '.join(
                    s.emailcode() for s in conflict_sections
                )
                log_lines.append(
                    "[CONFLICT] %s (ID %d): Time conflict with %s"
                    % (user.name(), user.id, conflict_names)
                )
                fail_count += 1
                continue

            result = section.preregister_student(
                user, overridefull=override_full
            )
            if result:
                log_lines.append(
                    "[OK] %s (ID %d): Successfully registered"
                    % (user.name(), user.id)
                )
                success_count += 1
            else:
                log_lines.append(
                    "[FULL] %s (ID %d): Section is full"
                    % (user.name(), user.id)
                )
                fail_count += 1

        log_lines.append("")
        log_lines.append(
            "Summary: %d succeeded, %d failed, %d skipped (already enrolled)"
            % (success_count, fail_count, skip_count)
        )

        logger.info(
            "Batch class registration: %d users -> section %s (ID %d): "
            "%d ok, %d fail, %d skip",
            users.count(), section.emailcode(), section.id,
            success_count, fail_count, skip_count
        )

        return "\n".join(log_lines)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
