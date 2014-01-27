======================
 Schema Simplification
======================

Up until now, a lot of miscellaneous data related to programs (including user
types, permissions, records, program names, class titles, and more) was stored
in the Data Tree and in User Bits. This was very bad for a variety of reasons.
The new schema migrates these separate types of data into their own fields or
new database tables.

.. contents:: :local:

User Types
----------

The type of a user (student, teacher, etc.) used to be tracked by a User Bit on
a user type Data Tree node. Now it is tracked by membership in a Django Group.
This is taken care of at account creation time, but if you need to manually
update the Groups a user is in, go to /admin/users/espuser/, find the user, and
change the selected Groups at the bottom of the page.

The Administrator Group is special. It gives admin privileges on the entire
site (except for the /admin pages). In most cases, you shouldn't manually add
someone to the Administrator Group. Instead, use /myesp/makeadmin/. To remove
someone's admin privileges, deselect them from the Administrator Group and
unselect "Staff status".

Besides the default user types, you can also create arbitrary Groups of users.
Just go to /admin/auth/group/ and create a new one, and then add the users you
want. Arbitrary Groups can be used with Permissions (see below).

Permissions
-----------

Permissions for a program (teacher/student registration deadlines) used to be
tracked by User Bits on registration Data Tree nodes, with expiration times
indicating the deadline for registration. Now they are tracked by Permission
objects. The interface on the front-end of the website remains mostly the same.
On the back-end, you can see these objects at /admin/users/permission/.

Just as before, you can set start and end times for Permissions. To indicate an
infinitely-lasting permission, leave the end date blank. You can give a
Permission to a specific user (use auto-complete in the user field, and leave
the role field blank) or to any Group of users (select a Group from the
drop-down box in the role field, and leave the user field blank). When
selecting a Group, you can use one of the default user types, or you can select
any arbitrary Group. For the permission type field, you can select from the
drop-down any of the usual registration deadlines. Finally, select the Program
that the Permission should apply to.

Records
-------

Records for a program (a student confirmed their registration, a teacher filed
out the teacher quiz, someone checked in, etc.) used to be tracked by User Bits
on various Data Tree nodes. Now they are tracked by Record objects. You can see
these objects on the back-end at /admin/users/record/. Record objects have an
event type (these are the same as before), a program, a user, and a time.

URLs
----

URLs for a program used to be determined by the program's Data Tree anchor.
For example, if the anchor was to the Data Tree node
Q/Programs/Splash/2013_Fall, then the urls would be of the form
/teach/Splash/2013_Fall/teacherreg, /learn/Splash/2013_Fall/studentreg, etc.
Now there is a url field on the Program object, which in this case would be
Splash/2013_Fall. From this, the website also knows that the program type is
Splash.

URLs for static html pages (QSD pages) used to also be determined by Data Tree
anchors. They too have a url field now, which is the full path (minus the .html
at the end) of the page. For example, teach/Splash/2013_Fall/teacher_shirt_info
is the url field for the QSD page at
/teach/Splash/2013_Fall/teacher_shirt_info.html.

Misc
----

The friendly program name (e.g. Splash Fall 2013) is now a field on the Program
object.

The class title is now a field on the Class Subject object.

