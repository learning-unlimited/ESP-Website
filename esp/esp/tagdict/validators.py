"""
Validators for Tag values that refer to form field names,
specifically for *_hide_fields tags.

Provides utilities to check whether the comma-separated field names
stored in hide_fields tags actually exist on the corresponding form
classes.  Used by the Tag admin form (to block invalid input) and by
profile / class-registration form __init__ methods (to log warnings).
"""

import logging

logger = logging.getLogger(__name__)

# Mapping of profile hide_fields tag keys to their form class info.
# Imports are performed lazily inside functions to avoid circular
# dependencies (the form modules import from tagdict themselves).
_PROFILE_HIDE_FIELDS_TAGS = {
    'student_profile_hide_fields': {
        'module': 'esp.users.forms.user_profile',
        'form_class': 'StudentProfileForm',
    },
    'teacher_profile_hide_fields': {
        'module': 'esp.users.forms.user_profile',
        'form_class': 'TeacherProfileForm',
    },
    'guardian_profile_hide_fields': {
        'module': 'esp.users.forms.user_profile',
        'form_class': 'GuardianProfileForm',
    },
    'educator_profile_hide_fields': {
        'module': 'esp.users.forms.user_profile',
        'form_class': 'EducatorProfileForm',
    },
    'volunteer_profile_hide_fields': {
        'module': 'esp.users.forms.user_profile',
        'form_class': 'VolunteerProfileForm',
    },
}

_TEACHERREG_HIDE_FIELDS_TAG = 'teacherreg_hide_fields'

# All tag keys that this module knows how to validate.
ALL_HIDE_FIELDS_TAG_KEYS = frozenset(
    list(_PROFILE_HIDE_FIELDS_TAGS.keys()) + [_TEACHERREG_HIDE_FIELDS_TAG]
)


def get_valid_field_names_for_tag(tag_key):
    """Return the set of valid (declared) field names for *tag_key*.

    Returns ``None`` if *tag_key* is not a recognised hide_fields tag.
    """
    if tag_key in _PROFILE_HIDE_FIELDS_TAGS:
        import importlib
        config = _PROFILE_HIDE_FIELDS_TAGS[tag_key]
        module = importlib.import_module(config['module'])
        form_class = getattr(module, config['form_class'])
        return set(form_class.declared_fields.keys())

    if tag_key == _TEACHERREG_HIDE_FIELDS_TAG:
        from esp.program.modules.forms.teacherreg import TeacherClassRegForm
        return set(TeacherClassRegForm.declared_fields.keys())

    return None


def validate_hide_fields_value(tag_key, tag_value):
    """Validate a comma-separated hide_fields tag value.

    Returns ``(valid_fields, invalid_fields, valid_field_set)`` when
    *tag_key* is a recognised hide_fields tag.

    Returns ``None`` when *tag_key* is not a hide_fields tag (i.e. no
    validation applies).

    Empty / whitespace-only values are considered valid (nothing to hide).
    """
    valid_field_set = get_valid_field_names_for_tag(tag_key)
    if valid_field_set is None:
        return None

    if not tag_value or not tag_value.strip():
        return ([], [], valid_field_set)

    # Normalise exactly the way the form __init__ methods do.
    field_names = [x.strip().lower() for x in tag_value.split(',') if x.strip()]

    valid = [f for f in field_names if f in valid_field_set]
    invalid = [f for f in field_names if f not in valid_field_set]

    return (valid, invalid, valid_field_set)
