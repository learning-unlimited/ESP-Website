"""
Validators for Tag values that refer to form field names, i.e. the
*_active_fields tags and the *_hide_fields tags they replaced.

Used by the Tag admin form to block invalid input.
"""

from esp.tagdict.active_fields import LEGACY_TAG_KEYS, SENTINELS

# Mapping of profile field-name tag keys to their form class info.
# Imports are performed lazily inside functions to avoid circular
# dependencies (the form modules import from tagdict themselves).
_PROFILE_FIELD_NAME_TAGS = {
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

# Each *_active_fields tag validates against the same fields as the
# *_hide_fields tag it replaced.
_PROFILE_FIELD_NAME_TAGS.update({
    active_key: _PROFILE_FIELD_NAME_TAGS[legacy_key]
    for active_key, legacy_key in LEGACY_TAG_KEYS.items()
    if legacy_key in _PROFILE_FIELD_NAME_TAGS
})

_TEACHERREG_HIDE_FIELDS_TAG = 'teacherreg_hide_fields'
_TEACHERREG_ACTIVE_FIELDS_TAG = 'teacherreg_active_fields'

# All tag keys that this module knows how to validate.
ALL_FIELD_NAME_TAG_KEYS = frozenset(
    list(_PROFILE_FIELD_NAME_TAGS.keys())
    + [_TEACHERREG_HIDE_FIELDS_TAG, _TEACHERREG_ACTIVE_FIELDS_TAG]
)


def get_valid_field_names_for_tag(tag_key):
    """Return the set of valid (declared) field names for *tag_key*.

    Returns ``None`` if *tag_key* is not a recognised field-name tag.
    """
    if tag_key in _PROFILE_FIELD_NAME_TAGS:
        import importlib
        config = _PROFILE_FIELD_NAME_TAGS[tag_key]
        module = importlib.import_module(config['module'])
        form_class = getattr(module, config['form_class'])
        return set(form_class.declared_fields.keys())

    if tag_key in (_TEACHERREG_HIDE_FIELDS_TAG, _TEACHERREG_ACTIVE_FIELDS_TAG):
        from esp.program.modules.forms.teacherreg import TeacherClassRegForm
        return set(TeacherClassRegForm.declared_fields.keys())

    return None


def validate_field_names_value(tag_key, tag_value):
    """Validate a comma-separated field-name tag value.

    Returns ``(valid_fields, invalid_fields, valid_field_set)`` when
    *tag_key* is a recognised field-name tag, else ``None``.

    Empty / whitespace-only values and the *_active_fields sentinels are valid.
    """
    valid_field_set = get_valid_field_names_for_tag(tag_key)
    if valid_field_set is None:
        return None

    if not tag_value or not tag_value.strip():
        return ([], [], valid_field_set)

    if tag_value.strip() in SENTINELS:
        return ([], [], valid_field_set)

    # Normalise exactly the way the tag parsing does.
    field_names = [x.strip().lower() for x in tag_value.split(',') if x.strip()]

    valid = [f for f in field_names if f in valid_field_set]
    invalid = [f for f in field_names if f not in valid_field_set]

    return (valid, invalid, valid_field_set)
