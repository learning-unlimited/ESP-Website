

Basic process of adding and using a new tag:
--------------------------------------------

To create a *global tag* (one applies to all programs), add a new line to the global tag dictionary ``all_global_tags`` in the
file https://github.com/learning-unlimited/ESP-Website/blob/main/esp/esp/tagdict/__init__.py.
To create a *program-specific tag*, add the new tag's name to the program tag dictionary `all_program_tags` in the same file as above.
Program tags are used with ``Tag.getProgramTag()`` or ``Tag.getBooleanTag()`` with a program argument in place of a boolean one in the
first coordinate.

The format for tags in either dictionary is ``'tag_name': (is the tag boolean?, 'some help text for admins')``, where the first
coordinate in the tuple determines whether the tag is retrieved by the function ``Tag.getBooleanTag`` (if so, set the first coordinate
to ``True``) or ``Tag.getTag`` (set it to ``False``). This formatting information is also in the comments of the file.

In order to make use of your new tag, find the file(s) where you want to use the tag's data, and make sure to include the
line ``from esp.tagdict.models import Tag``.
Use ``Tag.getTag('tag_name')`` (or the apprpriate variant, either ``getBooleanTag`` or ``getProgramTag``) to retrieve the value of the
tag in each file.


*Notes:*
Due to the import line, it is not possible to use tag data in `models\__init__.py`.
You may want to implement checks against the validity of the tag's data.
It is especially helpful to send a helpful error message to either the admin and the server log. :)

Please also add a description of your tag to the LU Wiki page on tags.
