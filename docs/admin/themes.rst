=============================
Customizing the Website Theme
=============================

.. contents:: :local:

Instructions for site admins
============================

To simplify front end design, there is now an app for configuring the front end
(appearance and navigation) of your site.  Behind the scenes, the app is
generating template overrides and CSS stylesheets based on your configuration.

The themes app can be accessed at https://[yoursite].learningu.org/themes/.  There are 3 steps:

* Select a theme (/themes/select/)

  You can choose from a set of pre-defined layouts.  We have adapted the most
  commonly used site designs and added two new ones geared towards simpler sites.
  You may need to force-refresh (hold the Shift key while refreshing the page)
  after loading a new theme in order to retrieve updated stylesheets.
  If there is a problem loading one of the themes, please contact web support.
  If you are switching from one theme to another, you should save a copy of your
  logo and any  modifications to the ``main.html`` and ``index.html`` template
  overrides before changing to the new theme because the process of switching
  will overwrite the current versions of these files.
  (If you don't know what template overrides are, you probably don't have any
  modifications, but you may certainly contact web support for help.)

See also the list of `Available Themes <available_themes.rst>`_.

* Set up the theme (/themes/setup/)

  You will be presented with a form for information needed by the theme to
  display properly.  Most themes will require certain text fragments (e.g. page
  title, group contact information) to be provided.  Some also have customizable
  navigation links.

* Customize the theme (/themes/customize/)

  This is an opportunity to differentiate your site from the others by altering
  its appearance without affecting functionality.  You will see a multi-section
  form.  Define a set of colors in the first section "Palette" and set color and
  shape options in the subsequent sections.  You can load and save a collection
  of these customizations (for instance, to change the color scheme with the
  season or with the next upcoming program).
  You may have to force-refresh (Shift + refresh) the page to see
  the updated color scheme.

  In addition to the color scheme, each theme has standard slots to include
  images. (The barebones theme has none, bigpicture has a background picture and
  a foreground logo, circles and floaty both have a slot for a logo, and fruitsalad
  has a logo and an optional "bubbles" front page.)
  To change the logo or other theme-related image, navigate to the Filebrowser by
  clicking on "Manage Media Files" in the admin toolbar on the left of the screen.
  Click the "images" folder then the "theme" folder, and find the image that matches
  the current logo (or other image you want to customize).
  Most logos are named ``logo.png``.
  Take note of the dimensions of the current file!
  Any image you upload should not differ dramatically in size or shape.
  Click "Change" next to the file you want to replace, and click "Delete" in the bottom
  left corner.
  Upload your own image to the same folder, and rename it to ``logo.png``
  (or whatever the name of the file you replaced was).
  To do so, go to the folder to which you uploaded the image, click "Change" next to
  your image, and change the "name" field.
  As with the color customization, you may have to force-refresh (Shift + refresh) the
  page where the image will be displayed to see the change.

Manual Theming
==============

You are not required to use the themes app; you may still manually edit
template overrides and upload media files to control the appearance of the
site.  (Please note that loading a theme will delete or overwrite your template
overrides, so you should keep copies if you are experimenting.)  The themes app
provides a simplified alternative and we hope that all of our sites will use it
as soon as their designs have been added to our repository as themes.

