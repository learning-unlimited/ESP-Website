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
  Email: web-team@learningu.org
"""

from esp.program.modules.base import (
    ProgramModuleObj,
    needs_teacher,
    main_call,
    aux_call,
)
from esp.utils.web import render_to_response
from esp.utils.decorators import json_response
from esp.application.models import StudentProgramApp, StudentClassApp

from django.http import HttpResponse, Http404
import json
from esp.utils.ids import get_by_id_or_404, parse_id


class AdmissionsDashboard(ProgramModuleObj):
    doc = """A dashboard for Junction core teachers to review applications for their class.
    Not to be confused with TeacherReviewApps, the app questions module."""

    @classmethod
    def module_properties(cls):
        return [
            {
                "admin_title": "Teacher Admissions Dashboard",
                "link_title": "Admissions Dashboard",
                "module_type": "teach",
                "choosable": 0,
            },
            {
                "admin_title": "Admin Admissions Dashboard",
                "link_title": "Admissions Dashboard",
                "module_type": "manage",
                "choosable": 0,
            },
        ]

    @main_call
    @needs_teacher
    def admissions(self, request, tl, one, two, module, extra, prog):
        if request.user.isAdmin(prog):
            classes = prog.classes()
        else:
            classes = request.user.getTaughtClassesFromProgram(prog)

        admin_status_choices = StudentProgramApp._meta.get_field(
            "admin_status"
        ).choices
        teacher_rating_choices = StudentClassApp._meta.get_field(
            "teacher_rating"
        ).choices
        decision_action_choices = [
            ("admit", "Admit"),
            ("unadmit", "Unadmit"),
            ("waitlist", "Waitlist"),
        ]

        return render_to_response(
            self.baseDir() + "admissions.html",
            request,
            {
                "classes": classes,
                "admin_status_choices": admin_status_choices,
                "teacher_rating_choices": teacher_rating_choices,
                "decision_action_choices": decision_action_choices,
            },
        )

    @aux_call
    @needs_teacher
    @json_response(None)
    def apps(self, request, tl, one, two, module, extra, prog):
        # Retrieve dictionaries rather than StudentClassApp instances.
        # StudentClassApp.__init__ dynamically selects a subclass using
        # app.app_type, which can cause additional database queries.
        classapps = StudentClassApp.objects.filter(
            app__program=prog,
        ).values(
            "id",
            "app_id",
            "app__admin_status",
            "app__admin_comment",
            "app__user__id",
            "app__user__first_name",
            "app__user__last_name",
            "subject_id",
            "subject__title",
            "teacher_rating",
            "teacher_ranking",
            "teacher_comment",
            "student_preference",
        )

        if not request.user.isAdmin(prog):
            classes = request.user.getTaughtClassesFromProgram(prog)
            classapps = classapps.filter(subject__in=classes)

        if extra:
            classapps = classapps.filter(subject_id=extra)

        if tl != "manage":
            classapps = classapps.filter(
                app__admin_status=StudentProgramApp.APPROVED
            )

        # Fetch admission and waitlist statuses in bulk instead of
        # performing additional queries for individual applications.
        decision_status_by_app = {}

        if tl == "manage" and request.user.isAdmin(prog):
            decision_classapps = StudentClassApp.objects.filter(
                            app__program=prog,
                            app_id__in=classapps.values("app_id"),
                            admission_status__in=(
                              StudentClassApp.ADMITTED,
                              StudentClassApp.WAITLIST,
                    ),

            ).values(
                "app_id",
                "admission_status",
                "subject__title",
            )

            for decision_classapp in decision_classapps:
                statuses = decision_status_by_app.setdefault(
                    decision_classapp["app_id"],
                    {"admitted": [], "waitlisted": []},
                )

                if (
                    decision_classapp["admission_status"]
                    == StudentClassApp.ADMITTED
                ):
                    statuses["admitted"].append(
                        decision_classapp["subject__title"]
                    )
                else:
                    statuses["waitlisted"].append(
                        decision_classapp["subject__title"]
                    )

            # Each student program application can have at most one
            # admitted class.
            for statuses in decision_status_by_app.values():
                assert len(statuses["admitted"]) <= 1
            subject_id = parse_id(extra)
            if subject_id is not None:
                classapps = classapps.filter(subject__id=subject_id)
            else:
                classapps = classapps.none()
        if tl != 'manage':
            classapps = classapps.filter(app__admin_status=StudentProgramApp.APPROVED)

        results = []

        for classapp in classapps:
            result = {
                "id": classapp["id"],
                "user": {
                    "id": classapp["app__user__id"],
                    "name": (
                        f"{classapp['app__user__first_name']} "
                        f"{classapp['app__user__last_name']}"
                    ),
                },
                "subject": {
                    "id": classapp["subject_id"],
                    "title": classapp["subject__title"],
                },
                "teacher_rating": classapp["teacher_rating"],
                "teacher_ranking": classapp["teacher_ranking"],
                "teacher_comment": classapp["teacher_comment"],
                "student_preference": classapp["student_preference"],
            }

            if tl == "manage" and request.user.isAdmin(prog):
                result["admin_status"] = classapp["app__admin_status"]
                result["admin_comment"] = classapp["app__admin_comment"]

                decision_status_lines = []
                statuses = decision_status_by_app.get(
                    classapp["app_id"],
                    {"admitted": [], "waitlisted": []},
                )

                for title in statuses["admitted"]:
                    decision_status_lines.append(f"Admitted: {title}")

                for title in statuses["waitlisted"]:
                    decision_status_lines.append(f"Waitlisted: {title}")

                result["decision_status"] = "\n".join(
                    decision_status_lines
                )

            results.append(result)

        return {"apps": results}

    @aux_call
    @needs_teacher
    def app(self, request, tl, one, two, module, extra, prog):
        try:
            classapp = StudentClassApp.objects.get(id=extra)
        except StudentClassApp.DoesNotExist:
            return self.goToCore(tl)  # XXX: more useful error here

        if not (
            request.user.isAdmin(prog)
            or classapp.subject
            in request.user.getTaughtClassesFromProgram(prog)
        ):
            classapp = get_by_id_or_404(StudentClassApp, extra)
        except Http404:
            return self.goToCore(tl) # XXX: more useful error here.
        if not (request.user.isAdmin(prog) or classapp.subject in request.user.getTaughtClassesFromProgram(prog)):
            return self.goToCore(tl)

        content = classapp.get_teacher_view(prog)
        return HttpResponse(content)

    @aux_call
    @needs_teacher
    @json_response(None)
    def update_apps(self, request, tl, one, two, module, extra, prog):
        if request.method == "POST":
            updated = []

            changes_data = request.POST.get("changes")
            if not changes_data:
                return {"success": 0, "error": "Missing changes data"}

            try:
                changes = json.loads(changes_data)
            except (ValueError, TypeError):
                return {"success": 0, "error": "Invalid JSON data"}

            for app_id, change in changes.items():
                try:
                    classapp = StudentClassApp.objects.get(id=app_id)
                except StudentClassApp.DoesNotExist:
                    continue

                if not (
                    request.user.isAdmin(prog)
                    or classapp.subject
                    in request.user.getTaughtClassesFromProgram(prog)
                ):
                    continue

                classapp.teacher_rating = change.get(
                    "teacher_rating", classapp.teacher_rating
                )
                classapp.teacher_ranking = change.get(
                    "teacher_ranking", classapp.teacher_ranking
                )
                classapp.teacher_comment = change.get(
                    "teacher_comment", classapp.teacher_comment
                )
                classapp.save()

                if request.user.isAdmin(prog):
                    app = classapp.app
                    app.admin_status = change.get(
                        "admin_status", app.admin_status
                    )
                    app.admin_comment = change.get(
                        "admin_comment", app.admin_comment
                    )
                    app.save()

                    decision_action = change.get("decision_action")

                    if decision_action == "admit":
                        classapp.admit()
                    elif decision_action == "unadmit":
                        classapp.unadmit()
                    elif decision_action == "waitlist":
                        classapp.waitlist()

                updated.append(app_id)

            return {"success": 1, "updated": updated}


    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = "modules"
