# Convert the deprecated *_hide_fields tags to the *_active_fields tags that
# replaced them, inverting each stored list of hidden fields into the list of
# fields to keep.

import logging

from django.db import migrations

from esp.tagdict.active_fields import ALL_FIELDS, LEGACY_TAG_KEYS, NO_FIELDS

logger = logging.getLogger(__name__)

ACTIVE_TAG_KEYS = {legacy: active for active, legacy in LEGACY_TAG_KEYS.items()}


def controllable_fields_by_tag():
    """ Map each legacy tag key to the field names its form lets admins remove.

    The forms are imported here, not at module scope, so an import failure
    cannot break a deploy; see hide_fields_to_active_fields.
    """
    from esp.tagdict.active_fields import TEACHERREG_HIDEABLE_REQUIRED_FIELDS, optional_field_names
    from esp.program.modules.forms.teacherreg import TeacherClassRegForm
    from esp.users.forms import user_profile

    forms_by_tag = {
        'student_profile_hide_fields': (user_profile.StudentProfileForm, ()),
        'teacher_profile_hide_fields': (user_profile.TeacherProfileForm, ()),
        'guardian_profile_hide_fields': (user_profile.GuardianProfileForm, ()),
        'educator_profile_hide_fields': (user_profile.EducatorProfileForm, ()),
        'volunteer_profile_hide_fields': (user_profile.VolunteerProfileForm, ()),
        'teacherreg_hide_fields': (TeacherClassRegForm, TEACHERREG_HIDEABLE_REQUIRED_FIELDS),
    }
    controllable = {}
    for key, (form_class, extra_fields) in forms_by_tag.items():
        names = optional_field_names(form_class) | set(extra_fields)
        #   Keep declaration order so the stored value matches the settings page
        controllable[key] = [name for name in form_class.declared_fields if name in names]
    return controllable


def split_names(value):
    return {name.strip().lower() for name in (value or '').split(',') if name.strip()}


def flush_tag_cache():
    """ Drop the cached tag lookups, which writes via the historical model miss. """
    from esp.tagdict.models import Tag as RealTag
    RealTag._getTag.delete_all()


def move_tag(Tag, source, target_key, value):
    """ Write value under target_key on the same target, and drop the source row. """
    if value is None:
        source.delete()
        return
    existing = Tag.objects.filter(key=target_key, content_type=source.content_type,
                                  object_id=source.object_id).first()
    if existing is None:
        Tag.objects.create(key=target_key, value=value, content_type=source.content_type,
                           object_id=source.object_id)
    source.delete()


def hide_fields_to_active_fields(apps, schema_editor):
    Tag = apps.get_model('tagdict', 'Tag')
    try:
        controllable = controllable_fields_by_tag()
    except Exception:
        logger.exception("Could not load the form classes to convert *_hide_fields tags; "
                         "leaving them in place (they are still honored at runtime).")
        return

    for legacy_key, fields in controllable.items():
        for tag in Tag.objects.filter(key=legacy_key):
            hidden = split_names(tag.value)
            active = [name for name in fields if name not in hidden]
            if len(active) == len(fields):
                #   Hiding nothing is the default, so no new tag is needed
                value = None
            elif not active:
                value = NO_FIELDS
            else:
                value = ",".join(active)
            move_tag(Tag, tag, ACTIVE_TAG_KEYS[legacy_key], value)

    flush_tag_cache()


def active_fields_to_hide_fields(apps, schema_editor):
    Tag = apps.get_model('tagdict', 'Tag')
    try:
        controllable = controllable_fields_by_tag()
    except Exception:
        logger.exception("Could not load the form classes to convert *_active_fields tags back.")
        return

    for legacy_key, fields in controllable.items():
        active_key = ACTIVE_TAG_KEYS[legacy_key]
        for tag in Tag.objects.filter(key=active_key):
            value = (tag.value or '').strip()
            if value == ALL_FIELDS or not value:
                hidden = []
            elif value == NO_FIELDS:
                hidden = list(fields)
            else:
                active = split_names(value)
                hidden = [name for name in fields if name not in active]
            move_tag(Tag, tag, legacy_key, ",".join(hidden) if hidden else None)

    flush_tag_cache()


class Migration(migrations.Migration):

    dependencies = [
        ('tagdict', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(hide_fields_to_active_fields, active_fields_to_hide_fields),
    ]
