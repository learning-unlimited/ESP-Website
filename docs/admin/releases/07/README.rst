============================================
 ESP Website Stable Release 06 release notes
============================================

.. contents:: :local:

Changelog
=========

New Django version
~~~~~~~~~~~~~~~~~~

TODO(mgersh, lua, benkraft)

Improvements to onsite scheduling grid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(lua)

Performance improvements
~~~~~~~~~~~~~~~~~~~~~~~~

This release included several changes which should help improve performance:

- Improved caching on student registration main page

- Improved documentation of program cap, which will improve performance

- Further improvements to the performance of student schedule generation


New scheduling checks
~~~~~~~~~~~~~~~~~~~~~

TODO(mgersh)

Sentry integration
~~~~~~~~~~~~~~~~~~

TODO(btidor)

Student schedule extra information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO(taylors, lua)

Minor feature additions and bugfixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Allowed onsite morphed users to bypass required modules

- Fixed grade options on onsite registration form

- Cleaned up or removed a lot of dead code

- Fixed a display issue in custom forms

- Fixed "any flag" filter in class search

- Added resource requests to class search results page

- Added ``created_at`` field to comm panel email models to aid in debugging
  issues

- Removed all usages of "QSD" and "quasi-static data" and replaced with
  "Editable" and "editable text"

- Improvements to dev setup infrastructure

- Miscellaneous fixes and improvements to various scripts

- Fixed a number of typos
