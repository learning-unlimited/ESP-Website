"""
Helpers for the *_active_fields tags, which choose the optional fields that
appear on the profile and class registration forms.
"""

import logging

logger = logging.getLogger(__name__)

#   Sentinels, needed because the tag settings forms delete a tag whose value is
#   empty, so "" cannot mean "no optional fields at all".
ALL_FIELDS = '_ALL_'
NO_FIELDS = '_NONE_'

SENTINELS = (ALL_FIELDS, NO_FIELDS)

#   Required teacher registration fields that can still be hidden, because a
#   teacherreg_default_* tag supplies the value the teacher would have picked.
TEACHERREG_HIDEABLE_REQUIRED_FIELDS = {
    'grade_min': 'teacherreg_default_min_grade',
    'grade_max': 'teacherreg_default_max_grade',
    'class_size_max': 'teacherreg_default_class_size_max',
}

#   The *_hide_fields tag that each *_active_fields tag replaces
LEGACY_TAG_KEYS = {
    'student_profile_active_fields': 'student_profile_hide_fields',
    'teacher_profile_active_fields': 'teacher_profile_hide_fields',
    'guardian_profile_active_fields': 'guardian_profile_hide_fields',
    'educator_profile_active_fields': 'educator_profile_hide_fields',
    'volunteer_profile_active_fields': 'volunteer_profile_hide_fields',
    'teacherreg_active_fields': 'teacherreg_hide_fields',
}


def optional_field_names(form_class):
    """ Return the declared field names of form_class that are not required. """
    return {name for name, field in form_class.declared_fields.items()
            if not field.required}


def active_fields_form_field(form_class, verbose_name, use_labels=False, extra_fields=()):
    """ Build the dual column tag settings widget for an *_active_fields tag. """
    #   Imported here (rather than at module scope) to avoid import loops
    from django import forms
    from django.contrib.admin.widgets import FilteredSelectMultiple

    controllable = optional_field_names(form_class) | set(extra_fields)
    choices = [(name, field.label if use_labels and field.label else name)
               for name, field in form_class.declared_fields.items()
               if name in controllable]
    return forms.MultipleChoiceField(
        choices=choices,
        widget=FilteredSelectMultiple(verbose_name, is_stacked=False),
    )


def parse_active_fields(tag_value, optional_fields, legacy_value=None, tag_key=None):
    """ Return the subset of optional_fields that should stay on the form.

    legacy_value is the deprecated *_hide_fields value, read only while
    tag_value is unset or _ALL_ so that upgrading a site keeps its settings.
    """
    optional_fields = set(optional_fields)
    value = tag_value.strip() if isinstance(tag_value, str) else tag_value

    if not value or value == ALL_FIELDS:
        if legacy_value:
            hidden = _split_names(legacy_value)
            _warn_unknown(tag_key, hidden - optional_fields, optional_fields, legacy=True)
            return optional_fields - hidden
        return optional_fields

    if value == NO_FIELDS:
        return set()

    active = _split_names(value)
    _warn_unknown(tag_key, active - optional_fields, optional_fields)
    return active & optional_fields


def parse_inactive_fields(tag_value, optional_fields, legacy_value=None, tag_key=None):
    """ The complement of parse_active_fields: the fields to remove or hide. """
    return set(optional_fields) - parse_active_fields(
        tag_value, optional_fields, legacy_value=legacy_value, tag_key=tag_key)


def inactive_teacherreg_fields(program):
    """ Return the TeacherClassRegForm fields hidden for program. """
    #   Imported here (rather than at module scope) to avoid import loops
    from esp.program.modules.forms.teacherreg import TeacherClassRegForm
    from esp.tagdict.models import Tag

    return parse_inactive_fields(
        Tag.getProgramTag('teacherreg_active_fields', program),
        optional_field_names(TeacherClassRegForm) | set(TEACHERREG_HIDEABLE_REQUIRED_FIELDS),
        legacy_value=Tag.getProgramTag('teacherreg_hide_fields', program),
        tag_key='teacherreg_active_fields')


def initial_choices(tag_value, choices, legacy_value=None, tag_key=None):
    """ Return the choice values to preselect in a tag settings widget. """
    choice_values = [str(choice[0]) for choice in choices]
    active = parse_active_fields(tag_value, choice_values,
                                 legacy_value=legacy_value, tag_key=tag_key)
    return [value for value in choice_values if value in active]


def value_from_choices(selected, choices):
    """ Return the tag value to store for the selected choice values. """
    if not selected:
        return NO_FIELDS
    choice_values = [str(choice[0]) for choice in choices]
    if set(selected) == set(choice_values):
        return ALL_FIELDS
    selected = set(selected)
    return ",".join(value for value in choice_values if value in selected)


def _split_names(value):
    return {name.strip().lower() for name in value.split(',') if name.strip()}


def _warn_unknown(tag_key, unknown, optional_fields, legacy=False):
    if not unknown:
        return
    logger.warning(
        "%s: %s %s not recognized optional field name(s) and will be ignored. "
        "Valid field names are: %s",
        LEGACY_TAG_KEYS.get(tag_key, tag_key) if legacy else (tag_key or 'active_fields'),
        ', '.join(sorted(unknown)),
        'is' if len(unknown) == 1 else 'are',
        ', '.join(sorted(optional_fields)),
    )
