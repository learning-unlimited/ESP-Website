

Basic process of creating and using a new tag:
--------------------------------------------

To create a *global tag* (one applies to all programs), add a new line to the global tag dictionary ``all_global_tags`` in the
file https://github.com/learning-unlimited/ESP-Website/blob/main/esp/esp/tagdict/__init__.py.
To create a *program-specific tag*, add the new tag's name to the program tag dictionary ``all_program_tags`` in the same file as above.

The format for tags in both dictionaries is ``'tag_name': (is the tag boolean?, 'some help text for admins', default value, category, show on tag settings page?)``. The first
variable in the tuple determines whether the tag is meant to contain only a boolean value (if so, set the first variable to ``True``)
or other data (set it to ``False``). The second variable is a string of help text that will be displayed for admins. The
third variable is the default value of the tag (type matters). The fourth variable is a string identifying the category of the tag, which is one of
``teach``, ``learn``, ``manage``, ``onsite``, ``volunteer``, or ``theme``. These categories are defined in the ``tag_categories`` dictionary in the same file above.
Finally, the fifth variable is a boolean identifying whether the tag should be shown on the tag settings page (``True`` for shown or ``False`` for not shown).

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
