"""Opt-in marker for autocompletes that non-staff users are allowed to call."""


def allow_non_staff_autocomplete(func):
    """Mark an ajax_autocomplete as safe to expose to non-staff users.

    Apply it directly to the function, inside @classmethod:

        @classmethod
        @allow_non_staff_autocomplete
        def ajax_autocomplete(cls, data, **kwargs):
            ...
    """
    func.allow_non_staff = True
    return func
