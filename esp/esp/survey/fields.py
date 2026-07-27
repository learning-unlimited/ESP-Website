"""Small helper field/descriptors used by the survey app.

Kept separate from `esp.survey.models` to avoid importing heavy model modules
from other apps at import time (which can create circular imports).
"""

from __future__ import absolute_import


class ListField(object):
    """Create a list type field descriptor.

    Allows packing lists/tuples into a delimited string stored in another field.
    """

    field_name = ''
    separator = '|'

    def __init__(self, field_name, separator='|'):
        self.field_name = field_name
        self.separator = separator

    def __get__(self, instance, class_):
        data = str(getattr(instance, self.field_name) or '').strip()
        if not data:
            return ()
        return tuple(data.split(self.separator))

    def __set__(self, instance, value):
        data = self.separator.join(map(str, value))
        setattr(instance, self.field_name, data)

