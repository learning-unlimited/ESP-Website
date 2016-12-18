============================================
 ESP Website Stable Release 09 release notes
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

New theme: bigpicture
~~~~~~~~~~~~~~~~~~~~~

This release adds a new theme, "bigpicture", based on the custom theme written
by Sean Zhu and used by Splash at Berkeley.  This theme looks a bit more modern
than the existing ones, and should better fit the needs of new chapters.  See
the `themes documentation <../../themes.rst>`_ for how to set up a
new theme.

Here's a screenshot of it live on `Berkeley's site
<https://berkeley.learningu.org>`_:

.. figure:: ../../images/themes/bigpicture.png

   Figure 1: "bigpicture" theme on Berkeley's site
