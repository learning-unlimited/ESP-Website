"""Helpers for ids that come from URLs or request parameters."""
from django.http import Http404
from django.shortcuts import get_object_or_404


def parse_id(value):
    """Return value as an int id, or None if it isn't one (e.g. 'abc')."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_by_id_or_404(model_or_qs, value, **filters):
    """get_object_or_404(..., id=value) that also copes with non-numeric ids."""
    pk = parse_id(value)
    if pk is None:
        raise Http404
    return get_object_or_404(model_or_qs, id=pk, **filters)


def filter_by_id(queryset, value, **filters):
    """queryset.filter(id=value, **filters), or an empty queryset if value isn't a valid id."""
    pk = parse_id(value)
    if pk is None:
        return queryset.none()
    return queryset.filter(id=pk, **filters)
