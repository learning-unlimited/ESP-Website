
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

from esp.program.modules.tests.ajaxschedulingmodule import AJAXSchedulingModuleTest  # noqa: F401
from esp.program.modules.tests.availabilitymodule import AvailabilityModuleTest  # noqa: F401
from esp.program.modules.tests.onsitecheckinmodule import OnSiteCheckinModuleTest  # noqa: F401
from esp.program.modules.tests.regprofilemodule import RegProfileModuleTest  # noqa: F401
from esp.program.modules.tests.studentreg import StudentRegTest  # noqa: F401
from esp.program.modules.tests.survey import SurveyTest  # noqa: F401
from esp.program.modules.tests.teachercheckinmodule import TeacherCheckinModuleTest  # noqa: F401
from esp.program.modules.tests.teacherclassregmodule import TeacherClassRegTest  # noqa: F401
from esp.program.modules.tests.jsondatamodule import JSONDataModuleTest  # noqa: F401
from esp.program.modules.tests.existence import ModuleExistenceTest  # noqa: F401
from esp.program.modules.tests.programprintables import ProgramPrintablesModuleTest  # noqa: F401
from esp.program.modules.tests.commpanel import CommunicationsPanelTest  # noqa: F401
from esp.program.modules.tests.resourcemodule import ResourceModuleTest  # noqa: F401
from esp.program.modules.tests.admincore import RegistrationTypeManagementTest, ModuleManagementConstraintsTest, ModuleManagementLinkTitleTest  # noqa: F401
from esp.program.modules.tests.adminclass import CancelClassTest  # noqa: F401
from esp.program.modules.tests.classsearchmodule import ClassSearchModuleTest  # noqa: F401
from esp.program.modules.tests.auth import ProgramModuleAuthTest  # noqa: F401
from esp.program.modules.tests.unenrollmodule import UnenrollModuleTest  # noqa: F401
from esp.program.modules.tests.testallviews import AllViewsTest  # noqa: F401
from esp.program.modules.tests.admintestingmodule import AdminTestingModuleTest  # noqa: F401
from esp.program.modules.tests.batchclassregmodule import BatchClassRegModuleTest
from esp.program.modules.tests.test_creditcard_required import (
    CreditCardRequiredTest, CreditCardCybersourceRequiredTest, CreditCardSelfBlockingTest
)
from esp.program.modules.tests.test_class_creation import (
    MakeAClassViewTest,
    ClassStatusOnEditTest,
    ClassTeacherListTest,
    ClassFormValidationTest,
    TeacherAvailabilityConsistencyTest,
)
