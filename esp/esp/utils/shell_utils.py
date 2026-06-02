'''Things that will be useful to have in shell_plus, which it will auto-import.'''

from django.db.models import F, Q, Count, Avg, Min, Max, Sum  # noqa: F401

import datetime  # noqa: F401
import numpy  # noqa: F401

from esp.utils.query_utils import nest_Q  # noqa: F401

from esp.program.modules.base import CoreModule, ProgramModuleObj  # noqa: F401

from esp.accounting.controllers import BaseAccountingController, GlobalAccountingController, IndividualAccountingController  # noqa: F401
from esp.customforms.DynamicForm import BaseCustomForm, CustomFormHandler, FormStorage, ComboForm, FormHandler  # noqa: F401
from esp.customforms.DynamicModel import DynamicModelHandler, DMH  # noqa: F401
from esp.customforms.linkfields import CustomFormsLinkModel, CustomFormsCache  # noqa: F401
from esp.program.controllers.classchange import ClassChangeController  # noqa: F401
from esp.program.controllers.classreg import ClassCreationController  # noqa: F401
from esp.program.controllers.confirmation import ConfirmationEmailController  # noqa: F401
from esp.program.controllers.lottery import LotteryAssignmentController  # noqa: F401
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator  # noqa: F401
from esp.program.controllers.resources import ResourceController  # noqa: F401
from esp.program.controllers.studentclassregmodule import RegistrationTypeController  # noqa: F401
from esp.program.controllers.studentregsanity import StudentRegSanityController  # noqa: F401
from esp.themes.controllers import ThemeController  # noqa: F401
from esp.users.controllers.usersearch import UserSearchController  # noqa: F401

import os
os.environ.setdefault("DJANGO_IS_IN_SCRIPT", "True")
# For convenience, set up a logger (and hide logging so people use the logger
# instead)
from logging import getLogger
logger = getLogger('esp.shell_plus')
