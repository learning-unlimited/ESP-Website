"""
Helpers for creating rows lazily without racing concurrent requests.

A plain check-then-create (including Model.objects.get_or_create() on fields
without a unique constraint) lets two concurrent requests both see no row and
both create one. These helpers serialize such creators by locking a related
row, such as the program or the user the new rows belong to.
"""
from django.db import transaction


def lock_row(instance):
    """
    Lock instance's row until the current transaction ends, so that callers
    locking the same row run one at a time. Must be called inside
    transaction.atomic(). Uses FOR NO KEY UPDATE, which does not block
    inserts of rows that reference this one.
    """
    # _meta rather than type(), which is wrong for lazy objects like request.user
    instance._meta.model._default_manager.select_for_update(no_key=True).get(pk=instance.pk)


def get_or_create_locked(model, lock_on, defaults=None, **kwargs):
    """
    Like model.objects.get_or_create(**kwargs), returning (obj, created), but
    safe when concurrent requests race to create the same row: creation is
    serialized by locking lock_on's row, so a concurrent caller waits, then
    finds the row the first one created. If earlier races left duplicates,
    the newest is returned instead of raising MultipleObjectsReturned.
    """
    matches = model._default_manager.filter(**kwargs).order_by('-pk')
    obj = matches.first()
    if obj is not None:
        return obj, False
    with transaction.atomic():
        lock_row(lock_on)
        obj = matches.first()
        if obj is not None:
            return obj, False
        return model._default_manager.create(**dict(kwargs, **(defaults or {}))), True
