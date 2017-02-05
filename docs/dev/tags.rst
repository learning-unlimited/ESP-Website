

Basic process of creating and using a new tag:
--------------------------------------------

To create a *global tag* (one applies to all programs), add a new line to the global tag dictionary ``all_global_tags`` in the
file https://github.com/learning-unlimited/ESP-Website/blob/main/esp/esp/tagdict/__init__.py.
To create a *program-specific tag*, add the new tag's name to the program tag dictionary ``all_program_tags`` in the same file as above.

The format for tags in both dictionaries is ``'tag_name': (is the tag boolean?, 'some help text for admins')``, where the first
variable in the tuple determines whether the tag is meant to contain only a boolean value (if so, set the first variable to ``True``)
or other data (set it to ``False``).

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
* Please also add a description of your tag to the `LU Wiki page on Tags <https://wiki.learningu.org/Customize_behavior_with_Tags>`_.
