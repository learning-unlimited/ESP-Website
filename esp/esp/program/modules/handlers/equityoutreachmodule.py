from __future__ import absolute_import

from django.db.models import Q

from esp.program.modules.base import ProgramModuleObj, main_call, needs_admin
from esp.program.modules.handlers.equityoutreach import EquityOutreachCohorts
from esp.utils.web import render_to_response


class EquityOutreachModule(ProgramModuleObj):
    doc = """Exposes at-risk student cohorts as user lists for Communications Panel and User Records."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Equity Outreach Navigator",
            "link_title": "Equity Outreach Navigator",
            "module_type": "manage",
            "seq": 35,
            "choosable": 1,
        }

    def students(self, QObject=False):
        """Register equity outreach cohorts as student lists for UserSearchController (comm panel, user records, etc.)."""
        result = {}
        for key in EquityOutreachCohorts.all_cohort_keys():
            qs = EquityOutreachCohorts.users_for_cohort(self.program, key)
            list_name = "equity_" + key
            if QObject:
                result[list_name] = Q(id__in=qs.values_list("id", flat=True))
            else:
                result[list_name] = qs.distinct()
        return result

    def studentDesc(self):
        """Descriptions for the equity outreach student lists."""
        return {
            "equity_" + key: EquityOutreachCohorts.cohort_label(key)
            for key in EquityOutreachCohorts.all_cohort_keys()
        }

    @main_call
    @needs_admin
    def equityoutreach(self, request, tl, one, two, module, extra, prog):
        context = {
            "program": prog,
            "cohorts": EquityOutreachCohorts.cohort_summaries(prog),
        }
        return render_to_response(self.baseDir() + "dashboard.html", request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = "modules"

