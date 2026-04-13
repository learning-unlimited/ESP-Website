'''Things that will be useful to have in shell_plus, which it will auto-import.'''

from django.db.models import F, Q, Count, Avg, Min, Max, Sum

import datetime
import numpy

from esp.utils.query_utils import nest_Q

from esp.program.modules.base import CoreModule, ProgramModuleObj

from esp.accounting.controllers import BaseAccountingController, GlobalAccountingController, IndividualAccountingController
from esp.customforms.DynamicForm import BaseCustomForm, CustomFormHandler, FormStorage, ComboForm, FormHandler
from esp.customforms.DynamicModel import DynamicModelHandler, DMH
from esp.customforms.linkfields import CustomFormsLinkModel, CustomFormsCache
from esp.program.controllers.classchange import ClassChangeController
from esp.program.controllers.classreg import ClassCreationController
from esp.program.controllers.confirmation import ConfirmationEmailController
from esp.program.controllers.lottery import LotteryAssignmentController
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.controllers.resources import ResourceController
from esp.program.controllers.studentclassregmodule import RegistrationTypeController
from esp.program.controllers.studentregsanity import StudentRegSanityController
from esp.themes.controllers import ThemeController
from esp.users.controllers.usersearch import UserSearchController

import os
os.environ.setdefault("DJANGO_IS_IN_SCRIPT", "True")
# For convenience, set up a logger (and hide logging so people use the logger
# instead)
from logging import getLogger
logger = getLogger('esp.shell_plus')


def choose_program(program_id=None, program_name=None, program_url=None):
    """Return a Program object using a unified, user-friendly selection mechanism.

    Can be used in two modes:

    1. Non-interactive (kwarg-supplied) — for scripts that already know the
       program they want via exactly one selector:

           program = choose_program(program_id=115)
           program = choose_program(program_name="Splash 2014")
           program = choose_program(program_url="Splash/2014_Fall")

       Supplying more than one selector raises ``ValueError``.  If the
       program is not found a
       ``Program.DoesNotExist`` exception is raised (same behaviour as a bare
       ``Program.objects.get(...)`` call, so existing scripts are not broken).

    2. Interactive (no kwargs) — for scripts that want the user to pick a
       program at runtime:

           program = choose_program()

       The function will:
         * Suggest the most temporally "current" programs (via
           ``Program.current_programs()``) numbered for quick selection.
                 * Accept ``i:<number>`` to pick from that suggestion list.
                 * Accept ``id:<number>``, a program name, or a program URL
                     as input.
         * Re-prompt on unrecognised input instead of crashing.

    Returns
    -------
    esp.program.models.Program
        The selected Program instance.

    Raises
    ------
    Program.DoesNotExist
        When a kwarg-supplied identifier does not match any program (only in
        non-interactive mode — interactive mode re-prompts instead).
    """
    # Lazy import to avoid circular-import issues at module load time.
    from esp.program.models import Program

    # ------------------------------------------------------------------
    # Non-interactive path: caller supplied an identifier as a kwarg.
    # ------------------------------------------------------------------
    provided_kwargs = [
        program_id is not None,
        program_name is not None,
        program_url is not None,
    ]

    if sum(provided_kwargs) > 1:
        raise ValueError("Supply at most one of program_id, program_name, program_url")

    if program_id is not None:
        return Program.objects.get(id=program_id)

    if program_name is not None:
        return Program.objects.get(name=program_name)

    if program_url is not None:
        return Program.objects.get(url=program_url)

    # ------------------------------------------------------------------
    # Interactive path: show suggestions and prompt the user.
    # ------------------------------------------------------------------
    suggestions = Program.current_programs()

    while True:
        print("\n--- Select a program ---")
        if suggestions:
            print("Suggested programs (based on current date):")
            for i, prog in enumerate(suggestions, start=1):
                print("  [{}] {} (id={}, url={})".format(i, prog.name, prog.id, prog.url))
        else:
            print("(No current programs found in the database.)")

        print("\nEnter one of:")
        if suggestions:
            print("  • i:<number> to select a suggested program (1-{})".format(len(suggestions)))
        print("  • id:<number> for a numeric program ID")
        print("  • A program name  (e.g. 'Splash 2014')")
        print("  • A program URL   (e.g. 'Splash/2014_Fall')")
        raw = input("\nYour choice: ").strip()

        if not raw:
            print("No input received — please try again.")
            continue

        # 1. Explicit suggestion index (i:<number>).
        lowered = raw.lower()
        if lowered.startswith('i:'):
            index_text = raw[2:].strip()
            if index_text.isdigit() and suggestions:
                number = int(index_text)
                if 1 <= number <= len(suggestions):
                    return suggestions[number - 1]
            print("Invalid suggestion index '{}'. Please try again.".format(raw))
            continue

        # 2. Explicit numeric program id (id:<number>).
        if lowered.startswith('id:'):
            id_text = raw[3:].strip()
            if not id_text.isdigit():
                print("Invalid program id '{}'. Please use id:<number>.".format(raw))
                continue
            try:
                return Program.objects.get(id=int(id_text))
            except Program.DoesNotExist:
                print("No program found with id={}.  Please try again.".format(id_text))
                continue

        # 3. Bare numeric input is ambiguous between suggestion index and id.
        if raw.isdigit():
            print("Numeric input is ambiguous. Use i:<number> or id:<number>.")
            continue

        # 4. Try as an exact name match.
        try:
            return Program.objects.get(name=raw)
        except Program.DoesNotExist:
            pass
        except Program.MultipleObjectsReturned:
            # Name is not unique, so multiple matches are possible; handle gracefully.
            print("Multiple programs share that name — please use an ID or URL instead.")
            continue

        # 5. Try as an exact URL match.
        try:
            return Program.objects.get(url=raw)
        except Program.DoesNotExist:
            pass

        print("Could not find a program matching '{}'. Please try again.".format(raw))
