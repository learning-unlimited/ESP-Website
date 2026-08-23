"""Shared constraints for learn and teach program modules."""

from esp.program.modules.base import ProgramModuleObj


PROFILE_MODULE_HANDLERS = (
    'StudentRegProfileModule',
    'TeacherRegProfileModule',
)

_REQUIRED_LOCKED_HANDLERS = frozenset(
    PROFILE_MODULE_HANDLERS + (
        'AvailabilityModule',
        'StudentRegTwoPhase',
    )
)
_NOT_REQUIRED_LOCKED_HANDLERS = frozenset(('StudentRegConfirm',))
_POSITION_LOCKED_HANDLERS = frozenset(
    PROFILE_MODULE_HANDLERS + ('StudentRegConfirm',)
)


def get_module_constraints(handler):
    """Return the locked fields for a module handler, if any."""
    required_locked = (
        handler in _REQUIRED_LOCKED_HANDLERS or
        'AcknowledgementModule' in handler
    )
    not_required_locked = (
        handler in _NOT_REQUIRED_LOCKED_HANDLERS or
        'CreditCardModule_' in handler
    )
    position_locked = (
        handler in _POSITION_LOCKED_HANDLERS or
        'CreditCardModule_' in handler
    )

    if not (required_locked or not_required_locked or position_locked):
        return None

    return {
        'required_locked': required_locked,
        'not_required_locked': not_required_locked,
        'position_locked': position_locked,
    }


def _update_modules(prog, filters, updates):
    for pmo in ProgramModuleObj.objects.filter(program=prog, **filters):
        for field, value in updates.items():
            setattr(pmo, field, value)
        pmo.save(update_fields=tuple(updates))


def enforce_module_constraints(prog):
    """Restore fields that module management must not change."""
    _update_modules(
        prog,
        {'module__handler__in': PROFILE_MODULE_HANDLERS},
        {'seq': 0, 'required': True},
    )
    _update_modules(
        prog,
        {'module__handler': 'AvailabilityModule'},
        {'required': True},
    )
    _update_modules(
        prog,
        {'module__handler': 'StudentRegTwoPhase'},
        {'required': True},
    )
    _update_modules(
        prog,
        {'module__handler': 'StudentRegConfirm'},
        {'seq': 99999, 'required': False},
    )
    _update_modules(
        prog,
        {'module__handler__contains': 'CreditCardModule_'},
        {'seq': 10000, 'required': False},
    )
    _update_modules(
        prog,
        {'module__handler__contains': 'AcknowledgementModule'},
        {'required': True},
    )
