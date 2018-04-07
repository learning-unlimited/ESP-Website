Other Utilities and Customizations
==================================

The ESP website has a bunch of other things in it that are useful to know.  Here are some of them:

Rendering and Templates
-----------------------
* We use a modified ``esp.utils.web.render_to_response`` instead of django's; it takes the template path, the request, and the context, and inserts useful things into the context, like information needed to render navbars, and the request.
* To render a block where admins can edit text (or images and other static content), put a ``{% load render_qsd %}`` somewhere, and then put a ``{% render_inline_qsd "name" %}`` or ``{% render_inline_program_qsd program "name" %}`` in where you want the block.  If you want it to have default text, put it between the tags ``{% inline_qsd_block "name" %}`` and ``{% end_inline_qsd_block %}`` or ``{% inline_program_qsd_block program "name" %}`` and ``{% end_inline_program_qsd_block %}``.
Note: in some cases, it may be necessary to write `prog` instead of `program`, depending on the specific template being modified.
* You almost always want your template to begin with ``{% extends "main.html" %}``, to inherit from the main site layout; then put the content between ``{% block content %}`` and ``{% endblock content %}`` tags.  Even if you don't want the main site layout, you may want to inherit ``{% extends "elements/html" %}`` to get our standard JS and CSS and such.
* We have a model in the database, ``esp.utils.TemplateOverride``, that makes it possible to override a template on a particular site by saving a new one in the database.  It's terrifying but also kind of useful. The theme editor uses these, and we often use them to customize printables.

Caching
-------
* We have a caching library, ``esp.cache``, which does a lot of magical and terrifying things to make the website not have to recompute data all the time.
* You can cache any function by putting an ``@cache_function`` decorator on top.  The hard part is of caching is making sure it always gets expired correctly, when any data that it depended on changes.  You do this by, after the function, putting ``function_name.depend_on_row()`` or similar calls, to make it depend on certain rows of the database.  The syntax is powerful but long, and probably best learned by looking at examples.
* Don't cache things unless you’re sure you're expiring the cache at the correct times!
* More details and the internals of the caching library are described in `<cache.rst>`_.

Testing
-------
* You should always test features manually on your dev server before you push them to a server.  Seriously, do it.
* We use the `Django Debug Toolbar <//django-debug-toolbar.readthedocs.org>`_, which will show up automatically on the right of all pages on a dev server.  It has useful things to tell you how slow your page is, and help debug errors.
* We also have automated tests; they don't cover as much of the codebase as we'd like, but they do exist.  They get automatically run by Travis when you push to Github; you can also run some locally, although you probably don't want to run the whole test suite locally.  You should write more tests!  See the Django testing docs for details on how.
