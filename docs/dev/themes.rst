Generic templates (themes app)
==============================
*Technical documentation*

Authors: 
   - Vikrant Varma <vikrant.varma94@gmail.com>   
   - Michael Price <price@learningu.org>

.. contents:: :local:

Context
-------
This application is used by different organizations, primarily chapters of
Learning Unlimited, that need different front-end designs for their Web
sites.  In the past, this was done by creating template overrides to supply
custom HTML code, and overriding the static files (e.g. images, stylesheets)
locally on the server.  That was too complicated for the majority of users,
so the generic templates system has been created to allow selecting and
parameterizing a theme (or "skin") for the site, using Web-based interfaces. 

This documentation explains how the generic templates system works, and how
new or modified front-end designs can be contributed to the repository as
themes.

Setup
-----

1) Make sure the server has all of the necessary libraries:

  ::

    apt-get install nodejs node-less


- Note: You will need version 1.3.1 of LESS (the one that comes with Ubuntu 13.04). You can install LESS from https://github.com/less/less.js (git clone, then git checkout v1.3.1) or, in Ubuntu, by adding this PPA: https://launchpad.net/~george-edison55/+archive/less
- Note: You will need version 0.10 or higher of Node.js.  You can install Node.js from https://github.com/joyent/node.git (git clonse, then git checkout v0.11.9-release).

2) Back up your database, or at least the template overrides.
3) Make sure the Web server user has execute and write permission on all of the directories under esp/public/media.  (The theme editor will be copying images and generating style files.)    
4) If you are using the MIT theme, you will need to manually delete your main.html template override in order to avoid seeing errors on every page before you load the theme.

Architecture
------------
Each theme consists of a set of pre-defined template overrides, images and
styles.  This information is stored in the code repository 
(esp/themes/theme_data directory).  The styles are stored in LESS
(http://lesscss.org) format and compiled into CSS with user-specified
parameters.

From the end user perspective, there are 3 steps to setting up their 
front-end design:

1) Selecting a theme, i.e. choosing which general design to use
2) Setting up the theme, i.e. providing information needed by the theme to render properly (e.g. navigation structure, group name and contact information)
3) Customizing the theme, i.e. changing optional parameters that affect appearance (like colors and fonts)
     
Each of these steps is handled by a view function in esp/themes/views.py:

1) Selecting: /themes/select -> selector()
2) Setup: /themes/setup -> configure()
3) Customizing: /themes/customize -> editor()
  
All operations are handled by the ThemeController class defined in
esp/themes/controllers.py.  The most important methods are:

- High level theme controls: clear_theme(), load_theme(), customize_theme()
- Back end driver functions: compile_css(), load_customizations(), save_customizations()

When someone selects a theme, the LESS stylesheet sources are all compiled
into a single CSS file (by default, public/media/styles/theme_compiled.css).
Any template overrides conflicting with the desired theme are removed.  The
media files provided by the theme are copied into the working directory.

Bootstrap is used to provide a baseline collection of styles that makes it
easier to create a decent looking theme.  However, it does complicate the
design of complex themes made by knowledgeable designers, so we may add an
option to exclude it from the builds in the future.

The setup and customization steps are kept separate because they collect
different types of information.  The backend storage of settings is also
done differently.

"Customization" refers specifically to LESS
stylesheet parameters, which are inferred from the LESS sources for each theme
(and a global list defined in 
public/media/theme_editor/less/variables_custom.less).  These are simple
colors, distances and strings that correspond directly to the stylesheet.
Customizations are stored in a user-named LESS file under
public/media/theme_editor/themes/ by default.

In contrast, "setup" refers to potentially more structured information that
can be used by template logic; it does not only affect the styling of the
output.  For example, the template may iterate over a list of navigation 
headings.  It may also want to know which contact information to display on 
every page.  These settings are specified by each theme in a Django form
class called ConfigForm.  The form is displayed by /themes/setup  and the 
responses are stored in the theme_template_control Tag.  (They are made 
available to the templates via the {{ theme }} context variable.)

Settings controlling operation are specified in esp/themes/settings.py.
Most of these don't need to changed, but you may find THEME_DEBUG (which
prints information to the shell) useful for debugging.

Creating themes
---------------
A new graphic design may be created by non-technical graphic designers and
content authors, who create a mockup consisting of a base HTML template,
CSS styles and images.  The process for contributing this design as a theme
is similar to the old process, but with some changes to ensure the theme
can be adjusted for the needs of other chapters.

Sources
+++++++
Each theme is packaged in a directory under esp/themes/theme_data as follows:

::

  esp/
    themes/
      theme_data/
        [theme_name]/
          __init__.py
          config_form.py
          images/
          less/
            main.less
            variables.less
            [other style files]
          scripts/
          templates/
            main.html
            [other template files]

The required sources for each theme are:

  1) Templates

     For each template you want to override, make an HTML file in the
     templates/ directory.  Many themes will only override the
     main.html template, but you can override more (e.g. index.html,
     users/student_schedule.html) as needed.
  
  2) Styles

     Any number of LESS stylesheet files can be placed in the less/
     directory.  These will be concatenated together and compiled
     to the CSS used by the site.  Note that LESS allows parameters to
     be specified with the following format:
     ::

       @box_heading_color: #333333;
       @box_rounding_radius: 8px;
       @heading_font: "Helvetica Neue";
       
     It's customary to collect the parameter assignments into a single
     file named variables.less.
  
  3) Images

     Place any images needed by the design in this directory.
     The images will be copied to /media/images/theme/ when the theme is
     loaded.
  
  4) Scripts

     If your design requires UI-specific Javascript code, any files that
     you place in the scripts/ directory will be copied to
     /media/scripts/theme/ when the theme is loaded.
  
  5) Configuration form

     In config_form.py, define a class named ConfigForm which subclasses
     esp.themes.forms.ThemeConfigurationForm.  This form can contain
     any Django form fields that you need to collect information expected
     by your template overrides
     
     The widget esp.utils.widgets.NavStructureWidget may be useful for
     collecting up to 2 levels of link structure.

Design process
++++++++++++++

Here is a recommended process for converting from an HTML/CSS mockup to a 
contributed theme.  Create a new Git branch relative to 'main' to
record your contributions.

First, look at the mockup and determine how you want the theme to be
customized.  Are there any chapter-specific text fragments?  Can the
sizes, line widths and/or shapes of layout elements be changed?  How 
many different colors are used and which should be adjustable?  Is the 
navigation structure adjustable?

Split your parameters into two groups.  Anything that shows up only in CSS
should probably be a stylesheet parameter, and you should put this into 
the less/variables.less file as specified by "2) Styles" above.
(These will appear in the "Advanced" section of the theme editor.)

Anything that shows up in your HTML output should be collected by the
setup form.  Write the desired form fields into a configuration form class 
as specified by "5) Configuration form" above.

Take your CSS sources and copy them to LESS files under the less/directory.  
Make sure to replace your hardcoded parameter values with references to the 
LESS variables you defined.  Copy scripts and images to their respective 
directories.

Now convert your HTML mockup into a main.html template override.  Reference
only the theme-specific scripts and images; all of the necessary Javascript
libraries and the compiled CSS will be included outside of this template
(by elements/html).  Replace chapter-specific information with references to
the {{ theme }} template variable.  For example, if your configuration form
has a field called 'sponsors' your template could say: "Thanks to our sponsors,
{{ theme.sponsors }}."

Create additional template overrides where the default templates would
significantly compromise the desired look and feel of the site.

Once you have a directory for your theme under esp/themes/theme_data, the
ThemeController will detect that the theme exists.  Try selecting it at 
/themes/select/ and going through the setup and customization process.
Ask the web-team list for help (and consult "Potential pitfalls" below)
if there are any unexpected problems. 

Make sure that you test the theme on a clean install of the site (e.g. a 
server that does not already have any of the images or styles that you were
using.)  This will ensure that you have included all of the necessary source 
files in the repository.

Create a pull request so the new theme can be reviewed before it is merged 
into the main branch.

Potential pitfalls
++++++++++++++++++

If there are any errors in your LESS code, you may not be able to compile CSS.
Turn on THEME_DEBUG to generate intermediate LESS output and print debugging
information to the shell.

The current system is not compatible with all versions of LESS and Node.js.
You may need to manually install compatible versions.  Version 1.3.1 of LESS
is known to work properly.

Note that all pages on the site are going to see all of the style information
provided by the LESS files.  So, don't expect that one page can use <h2> and 
have it look different from an <h2> somewhere else (which could have been done
in the past by including different CSS files).  Use selectors to differentiate 
between elements.

Further setup and usage information is available at:
  http://wiki.learningu.org/Generic_Templates



