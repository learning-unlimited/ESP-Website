"""
Helpers for the ``*_active_fields`` tags.

These tags let admins choose which *optional* fields appear on the profile
and class-registration forms.  They replace the older ``*_hide_fields``
tags, which listed the fields to remove instead.

The stored value is either one of the sentinels below or a comma-separated
list of field names.  Sentinels are needed because the tag-settings forms
delete a tag whose value is empty, so an empty string cannot be used to mean
"no optional fields at all".

Form classes are imported lazily by the callers (the form modules import
from tagdict themselves), so nothing here imports them at module scope.
"""

import logging

logger = logging.getLogger(__name__)

#   Every optional field is active.  This is the default for every
#   *_active_fields tag, so an unset tag leaves the form untouched.
ALL_FIELDS = '_ALL_'

#   No optional field is active.
NO_FIELDS = '_NONE_'

SENTINELS = (ALL_FIELDS, NO_FIELDS)

#   Required teacher registration fields that the form can still hide, because a
#   teacherreg_default_* tag supplies the value the teacher would have picked.
TEACHERREG_HIDEABLE_REQUIRED_FIELDS = {
    'grade_min': 'teacherreg_default_min_grade',
    'grade_max': 'teacherreg_default_max_grade',
    'class_size_max': 'teacherreg_default_class_size_max',
}

#   The *_hide_fields tag that each *_active_fields tag replaces.  The legacy
#   tag is still read when the new one is unset, so upgrading a site does not
#   silently restore fields that an admin had hidden.
LEGACY_TAG_KEYS = {
    'student_profile_active_fields': 'student_profile_hide_fields',
    'teacher_profile_active_fields': 'teacher_profile_hide_fields',
    'guardian_profile_active_fields': 'guardian_profile_hide_fields',
    'educator_profile_active_fields': 'educator_profile_hide_fields',
    'volunteer_profile_active_fields': 'volunteer_profile_hide_fields',
    'teacherreg_active_fields': 'teacherreg_hide_fields',
}


def optional_field_names(form_class):
    """Return the declared field names of *form_class* that are not required.

    Only these fields are offered in the tag-settings widgets, and only these
    are ever removed from a form, so fields that are added or made optional at
    runtime are never dropped by a tag the admin cannot see.
    """
    return {name for name, field in form_class.declared_fields.items()
            if not field.required}


def active_fields_form_field(form_class, verbose_name, use_labels=False, extra_fields=()):
    """Build the dual-column tag-settings widget for an *_active_fields tag.

    The chosen column lists the optional fields that will appear on
    *form_class*; required fields are not offered because they can never be
    removed, unless they are named in *extra_fields*.  ``FilteredSelectMultiple``
    needs the admin JS and CSS, which the tag settings template pulls in.
    """
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
    """Return the subset of *optional_fields* that should stay on the form.

    *tag_value* is the raw ``*_active_fields`` tag value; *legacy_value* is the
    raw ``*_hide_fields`` value, used only when *tag_value* is unset or is the
    ``_ALL_`` sentinel.  *tag_key* is used for log messages only.
    """
    optional_fields = set(optional_fields)
    value = tag_value.strip() if isinstance(tag_value, str) else tag_value

    if not value or value == ALL_FIELDS:
        #   Fall back to the tag this one replaced, if it is still set.
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
    """The complement of :func:`parse_active_fields`: fields to remove/hide."""
    return set(optional_fields) - parse_active_fields(
        tag_value, optional_fields, legacy_value=legacy_value, tag_key=tag_key)


def inactive_teacherreg_fields(program):
    """Return the optional TeacherClassRegForm fields hidden for *program*.

    Imported lazily because teacherreg imports from tagdict itself.
    """
    from esp.program.modules.forms.teacherreg import TeacherClassRegForm
    from esp.tagdict.models import Tag

    return parse_inactive_fields(
        Tag.getProgramTag('teacherreg_active_fields', program),
        optional_field_names(TeacherClassRegForm) | set(TEACHERREG_HIDEABLE_REQUIRED_FIELDS),
        legacy_value=Tag.getProgramTag('teacherreg_hide_fields', program),
        tag_key='teacherreg_active_fields')


def initial_choices(tag_value, choices, legacy_value=None, tag_key=None):
    """Return the list of choice values to preselect in a tag-settings widget.

    ``MultipleChoiceField.initial`` has to be a list of valid choice values, so
    the sentinels and the comma-separated storage format are expanded here.
    """
    choice_values = [str(choice[0]) for choice in choices]
    active = parse_active_fields(tag_value, choice_values,
                                 legacy_value=legacy_value, tag_key=tag_key)
    #   Preserve the order the choices are declared in rather than set order.
    return [value for value in choice_values if value in active]


def value_from_choices(selected, choices):
    """Return the tag value to store for the *selected* choice values."""
    if not selected:
        return NO_FIELDS
    choice_values = [str(choice[0]) for choice in choices]
    if set(selected) == set(choice_values):
        return ALL_FIELDS
    #   Store in the order the choices are declared so the value is stable
    return ",".join(value for value in choice_values if value in set(selected))


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
