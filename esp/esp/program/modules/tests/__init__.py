
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

from esp.program.modules.tests.test_ajaxschedulingmodule import AJAXSchedulingModuleTest
from esp.program.modules.tests.test_availabilitymodule import AvailabilityModuleTest
from esp.program.modules.tests.test_onsitecheckinmodule import OnSiteCheckinModuleTest
from esp.program.modules.tests.test_studentregprofilemodule import StudentRegProfileModuleTest, RegistrationProfileFlowTest
from esp.program.modules.tests.test_studentreg import StudentRegTest, RegistrationTypeVisibilityTest
from esp.program.modules.tests.test_survey import SurveyTest
from esp.program.modules.tests.test_teachercheckinmodule import TeacherCheckinModuleTest
from esp.program.modules.tests.test_teacherclassregmodule import TeacherClassRegTest, TeacherScheduleDeadlineTest
from esp.program.modules.tests.test_jsondatamodule import JSONDataModuleTest
from esp.program.modules.tests.test_existence import ModuleExistenceTest
from esp.program.modules.tests.test_programprintables import ProgramPrintablesModuleTest
from esp.program.modules.tests.test_commpanel import CommunicationsPanelTest
from esp.program.modules.tests.test_resourcemodule import ResourceModuleTest
from esp.program.modules.tests.test_admincore_management import RegistrationTypeManagementTest, ModuleManagementConstraintsTest, ModuleManagementLinkTitleTest
from esp.program.modules.tests.test_adminclass import CancelClassTest
from esp.program.modules.tests.test_studentregmodules import StudentExtraCostsTest, StudentRegCoreTest, StudentRegPhaseZeroTest, StudentRegConfirmTest, LotteryStudentRegTest, StudentAcknowledgementTest, StudentLunchSelectionTest, StudentSurveyModuleTest, StudentCertModuleTest, StudentOnsiteTest, StudentClassRegModuleTest
from esp.program.modules.tests.test_studentextracosts import (
    StudentExtraCostsTest as StudentExtraCostsCustomAmountTest,
)
from esp.program.modules.tests.test_classsearchmodule import ClassSearchModuleTest
from esp.program.modules.tests.test_classflagmodule import ClassFlagModuleTest
from esp.program.modules.tests.test_auth import ProgramModuleAuthTest
from esp.program.modules.tests.test_unenrollmodule import UnenrollModuleTest
from esp.program.modules.tests.test_testallviews import AllViewsTest
from esp.program.modules.tests.test_equityoutreach import EquityOutreachTest
from esp.program.modules.tests.test_admintestingmodule import AdminTestingModuleTest
from esp.program.modules.tests.test_openclasses import OpenClassesPublicTest
from esp.program.modules.tests.test_get_hours import GetHoursQueryCountTest, GetHoursApprovedFilterTest, GetHoursScheduledFilterTest, StaticHoursTest
from esp.program.modules.tests.test_batchclassregmodule import BatchClassRegModuleTest
from esp.program.modules.tests.test_formstackappmodule import FormstackAppModuleTest
from esp.program.modules.tests.test_creditcard_required import (
    CreditCardRequiredTest, CreditCardCybersourceRequiredTest, CreditCardSelfBlockingTest
)
from esp.program.modules.tests.test_grouptextmodule import GroupTextModuleSendMessagesTest
from esp.program.modules.tests.test_deactivationmodule import DeactivationModuleTest
from esp.program.modules.tests.test_class_creation import (
    MakeAClassViewTest,
    ClassStatusOnEditTest,
    ClassTeacherListTest,
    ClassFormValidationTest,
    TeacherAvailabilityConsistencyTest,
    ClassCreationControllerUnitTest,
)
from esp.program.modules.tests.test_resolve_user import ResolveUserTest
from esp.program.modules.tests.test_module_progress import RegistrationProgressTagTest, RequiredModuleProgressIntegrationTest
from esp.program.modules.tests.test_enrolled_split import EnrolledSplitViewTest
from esp.program.modules.tests.test_accountingmodule import AccountingModuleTest
from esp.program.modules.tests.test_lotteryfrontendmodule import LotteryFrontendModuleTest
from esp.program.modules.tests.test_student_reg_phase_zero import StudentRegPhaseZeroTestCase
from esp.program.modules.tests.test_teacher_review_apps import TeacherReviewAppsTest
from esp.program.modules.tests.test_schedulingcheckmodule import SchedulingCheckModuleTest
from esp.program.modules.tests.test_scheduling_check import (
    SchedulingCheckHelpersTest,
    SchedulingCheckModuleViewTest,
    SchedulingCheckDiagnosticsTest,
)
from esp.program.modules.tests.test_student_reg_phase_zero_manage import StudentRegPhaseZeroManageTest
from esp.program.modules.tests.test_teacherevents import TeacherEventsModuleTest, TeacherEventsCalendarDataTest
from esp.program.modules.tests.test_studentlunchselection import StudentLunchSelectionTest as StudentLunchSelectionModuleTest
from esp.program.modules.tests.test_teachereventsmanage_module import (
    TeacherEventsManageModulePropertiesTest,
    TeacherEventsManageModuleAdminSearchTest,
    TeacherEventsManageModuleIsStepTest,
    TeacherEventsManageModuleAvailabilityRoleTest,
    TeacherEventsManageModuleIsCompletedTest,
    TeacherEventsManageModuleViewTest,
)
from esp.program.modules.tests.test_studentregtwophase import StudentRegTwoPhaseTest, StudentRegTwoPhaseMisconfiguredTest
from esp.program.modules.tests.test_onsiteattendance import TestTimesAttendingClass, TestTimesCheckedIn
from esp.program.modules.tests.test_addclass_concurrency import AddClassConcurrencyRegressionTest
from esp.program.modules.tests.test_usergroupmodule import UserGroupModuleTests
from esp.program.modules.tests.test_surveymanagement import SurveyManagementTest
from esp.program.modules.tests.test_onsitecheckoutmodule import OnSiteCheckoutModuleTest
from esp.program.modules.tests.test_studentjunctionappmodule import StudentJunctionAppModuleTest

from esp.program.modules.tests.test_donationmodule import DonationFormTest, DonationModuleTest
from esp.program.modules.tests.test_draft_creation import MakeAClassDraftTest
from esp.program.modules.tests.test_customform_assets import CustomFormAssetsTest
from esp.program.modules.tests.test_customform_reopen import CustomFormReopenTest
