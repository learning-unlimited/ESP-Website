============================================
 ESP Website Stable Release 08 release notes
============================================

.. contents:: :local:

Changelog
=========

Deletion of login by birthday or school
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before this release, the website included the option for students to log in by
selecting their birthday or school from a list, and then selecting their
username from a list of all student accounts with that birthday or from that
school. This feature has been deleted because it leaks user data: anyone could
go through the list of birthdays or schools one by one and collect this
information for all of our students. Users having trouble logging in are now
encouraged to use the password reset page.

Improvements to user search
~~~~~~~~~~~~~~~~~~~~~~~~~~~
With this release, the User Search box returns users whose cell phone number or
*parent's* email address matches the query, in addition to the matches that were
previously returned. The search is also more robust to case and whitespace issues.

Improvements to class search
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
With this release, class search allows you to edit your search at the top of the search page.  The results page also includes a new button to email the teachers of a class, a new button to show all classes and all flags which have comments, and an option to randomize the order of search results, along with a minor bugfix.
