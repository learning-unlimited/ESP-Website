"""
This file was generated with the customdashboard management command, it
contains the two classes for the main dashboard and app index dashboard.
You can customize these classes as you want.

To activate your index dashboard add the following to your settings.py::
    ADMIN_TOOLS_INDEX_DASHBOARD = 'admintoolsdash.CustomIndexDashboard'

And to activate the app index dashboard::
    ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'admintoolsdash.CustomAppIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from admin_tools.dashboard import modules, Dashboard, AppIndexDashboard
from admin_tools.utils import get_admin_site_name, get_avail_models
from django.apps import apps as django_apps


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for esp.
    """
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            _('Quick links'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_('Return to site'), '/'],
                [_('Filebrowser'), '/admin/filebrowser/browse'],
                [_('Theme Settings'), '/themes']
            ]
        ))

        # separate each app into a separate group
        items = get_avail_models(context['request'])
        apps = {}

        for model, perms in items:
            app_label = model._meta.app_label
            if app_label not in apps:
                apps[app_label] = {
                    'title': django_apps.get_app_config(app_label).verbose_name,
                    'models': []
                }
            apps[app_label]['models'].append('%s.%s' % (model.__module__, model.__name__))

        for app in sorted(apps.keys()):
            # append an app list module for each set of models
            self.children.append(modules.ModelList(
                _(apps[app]['title']),
                models=apps[app]['models'],
            ))

        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=10
        ))


class CustomAppIndexDashboard(AppIndexDashboard):
    """
    Custom app index dashboard for esp.
    """

    # we disable title because its redundant with the model list module
    title = ''

    def __init__(self, *args, **kwargs):
        AppIndexDashboard.__init__(self, *args, **kwargs)

        # append a model list module and a recent actions module
        self.children += [
            modules.ModelList(
                self.app_title,
                models = self.models,
            ),
            modules.RecentActions(
                _('Recent Actions'),
                #include_list=self.models,
                limit=10
            )
        ]

    def init_with_context(self, context):
        """
        Use this method if you need to access the request context.
        """
        return super(CustomAppIndexDashboard, self).init_with_context(context)
