"""
AuditedModelAdmin
=================
A Django ModelAdmin mixin that writes an AuditLogEntry for every
create / update / delete / bulk-action performed through the admin UI.

Usage
-----
    from esp.utils.audit import AuditedModelAdmin

    class MyAdmin(AuditedModelAdmin, admin.ModelAdmin):
        ...
"""

import json
import logging

logger = logging.getLogger(__name__)

# Fields whose changes are too noisy or irrelevant to audit.
IGNORED_FIELDS = frozenset({
    'last_login',
    'updated',
    'updated_at',
    'modified',
    'modified_at',
    'password',       # never log raw password hashes
})


def _serialize_value(value):
    """Best-effort JSON-safe representation of a field value."""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _diff_objects(old_obj, new_obj, form):
    """
    Return a dict of {field_name: [old_value, new_value]} for every field
    that changed between *old_obj* (pre-save snapshot) and *new_obj* (saved).
    Only fields present in the submitted form are considered, and fields
    listed in IGNORED_FIELDS are skipped.
    """
    changes = {}
    for field_name in form.changed_data:
        if field_name in IGNORED_FIELDS:
            continue
        old_val = _serialize_value(getattr(old_obj, field_name, None))
        new_val = _serialize_value(getattr(new_obj, field_name, None))
        if old_val != new_val:
            changes[field_name] = [old_val, new_val]
    return changes


def _get_audit_model():
    """Lazy import to avoid circular imports at module load time."""
    from esp.utils.models import AuditLogEntry
    return AuditLogEntry


def _get_content_type(obj):
    """Return the ContentType for *obj*, or None on failure."""
    try:
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get_for_model(obj)
    except Exception:
        return None


class AuditedModelAdmin:
    """
    Mixin for ModelAdmin subclasses.
    Inherit *before* ModelAdmin so that save_model / delete_model /
    response_action are properly overridden::

        class MyAdmin(AuditedModelAdmin, admin.ModelAdmin): ...
    """

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _write_log(self, request, action, obj, changes=None, extra=''):
        AuditLogEntry = _get_audit_model()
        try:
            AuditLogEntry.objects.create(
                actor=request.user,
                action=action,
                content_type=_get_content_type(obj),
                object_id=obj.pk if obj.pk else None,
                object_repr=str(obj)[:500],
                actor_ip=request.META.get('REMOTE_ADDR'),
                changes=changes,
                extra=extra,
            )
        except Exception:
            # Never let audit logging crash the actual admin action.
            logger.exception(
                'AuditLog write failed for %s %s pk=%s',
                action, obj.__class__.__name__, obj.pk,
            )

    def _write_bulk_log(self, request, action_name, queryset):
        AuditLogEntry = _get_audit_model()
        pks = list(queryset.values_list('pk', flat=True))
        try:
            # Use ContentType of the queryset's model for consistency.
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(queryset.model)
        except Exception:
            ct = None
        try:
            AuditLogEntry.objects.create(
                actor=request.user,
                action=AuditLogEntry.ACTION_BULK,
                content_type=ct,
                object_id=None,
                object_repr=f'{len(pks)} object(s)',
                actor_ip=request.META.get('REMOTE_ADDR'),
                changes=None,
                extra=f'action="{action_name}" pks={pks}',
            )
        except Exception:
            logger.exception(
                'AuditLog bulk write failed for action=%s model=%s',
                action_name, queryset.model.__name__,
            )

    # ------------------------------------------------------------------ #
    #  Django admin hooks                                                  #
    # ------------------------------------------------------------------ #

    def save_model(self, request, obj, form, change):
        AuditLogEntry = _get_audit_model()

        if change:
            # Fetch pre-save state for diffing.
            try:
                old_obj = obj.__class__.objects.get(pk=obj.pk)
            except obj.__class__.DoesNotExist:
                old_obj = obj
            super().save_model(request, obj, form, change)
            changes = _diff_objects(old_obj, obj, form)
            self._write_log(request, AuditLogEntry.ACTION_UPDATE, obj, changes=changes)
        else:
            super().save_model(request, obj, form, change)
            self._write_log(request, AuditLogEntry.ACTION_CREATE, obj)

    def delete_model(self, request, obj):
        self._write_log(request, _get_audit_model().ACTION_DELETE, obj)
        super().delete_model(request, obj)

    def response_action(self, request, queryset):
        """Intercept bulk actions to log them before they run."""
        action = request.POST.get('action', '')
        if action:
            self._write_bulk_log(request, action, queryset)
        return super().response_action(request, queryset)

