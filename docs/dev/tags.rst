

Basic process of creating and using a new tag:
----------------------------------------------

To create a *global tag* (one applies to all programs), add a new item to the global tag dictionary ``all_global_tags`` in the
file https://github.com/learning-unlimited/ESP-Website/blob/main/esp/esp/tagdict/__init__.py.
To create a *program-specific tag*, add a new item to the program tag dictionary ``all_program_tags`` in the same file as above.

The format for tags in both dictionaries is as follows::

    'key': {
      'is_boolean': is tag used with getBooleanTag? (boolean),
      'help_text': 'some help text for admins',
      'default': default value,
      'category': 'category name',
      'is_setting': show on tag settings page? (boolean),
      (optional) 'field': a django form field instance
    }

The 'is_boolean' item in the dictionary determines whether the tag is meant to contain only a boolean value (if so, set the value to ``True``)
or other data (set the value to ``False``). The 'help_text' item is a string of help text that will be displayed for admins. The
'default' item is the default value of the tag (type matters). The 'category' item is a string identifying the category of the tag, which is one of
``teach``, ``learn``, ``manage``, ``onsite``, ``volunteer``, or ``theme``. These categories are defined in the ``tag_categories`` dictionary in the same file above.
The 'is_setting' item is a boolean identifying whether the tag should be shown on the tag settings page (``True`` for shown or ``False`` for not shown).
Finally, the 'field' item is optional and can be used to specify a custom form field (the default for a boolean tag is forms.BooleanField(); the default
for a non-boolean tag is forms.CharField()). The value should be an instance of a django form field (e.g. forms.IntegerField()).

In order to make use of your new tag, find the file(s) where you want to use the tag's data, and make sure to include the
line ``from esp.tagdict.models import Tag``.
Use ``Tag.getTag('tag_name')`` to retrieve the value of a non-boolean global Tag.
For boolean Tags, use ``Tag.getBooleanTag('tag_name')``.
Program tags can be used with ``Tag.getProgramTag('tag_name', program)`` or by passing a program argument to ``Tag.getBooleanTag()``.


*Notes:*

* It is not recommended (and in some cases not possible) to access  tag data at import time because tag data is stored in the database.
* You may want to implement checks against the validity of the tag's data.
  For instance, it is helpful to send a descriptive error message to an admin who's trying access invalid tag data (unfortunately, there
  is not currently an easy way to notify an admin immediately when an invalid tag is set in the admin panel).
