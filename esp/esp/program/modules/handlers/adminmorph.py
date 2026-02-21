"""
DEPRECATED: AdminMorph module stub.

This file exists as a deploy-time safety shim.  The AdminMorph
ProgramModule is removed by migration 0047_remove_adminmorph; until that
migration has been applied to a running instance the ProgramModule DB
row (handler='AdminMorph') may still be present and ProgramModule.
getPythonClass() will attempt to import this module.  Without this file
the import raises CannotGetClassException and crashes module loading.

Once 0047_remove_adminmorph has run on every target environment this
file may be deleted entirely.
"""
import warnings

from esp.program.modules.base import ProgramModuleObj


class AdminMorph(ProgramModuleObj):
    """Stub for the removed AdminMorph handler.

    All real functionality has been deleted.  This class only exists so
    that getPythonClass() does not raise CannotGetClassException during
    the window between code deployment and database migration.
    """

    @classmethod
    def module_properties(cls):
        # stacklevel=1 pins the warning location to this warn() call rather
        # than to each individual caller.  Python's default "once" filter
        # then suppresses the warning after the first emission per interpreter
        # session, regardless of how many times module_properties() is called
        # or from how many different places, preventing log flooding.
        warnings.warn(
            "AdminMorph is deprecated and will be removed once migration "
            "0047_remove_adminmorph has been applied.",
            DeprecationWarning,
            stacklevel=1,
        )
        return {
            "admin_title": "User Morphing Capability (DEPRECATED)",
            "link_title": "Morph into User (DEPRECATED)",
            "module_type": "manage",
            "seq": 34,
            "choosable": 0,
        }

    class Meta:
        # managed=False prevents Django from generating new migrations for this
        # stub after migration 0047_remove_adminmorph has deleted the model from
        # the migration state.  The class remains importable so that
        # getPythonClass() does not raise CannotGetClassException during the
        # deploy window before the migration is applied.
        managed = False
        app_label = "modules"
