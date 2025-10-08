
from __future__ import absolute_import
import six
from io import open
from six.moves import range
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.middleware import ESPError
from esp.users.models import admin_required
from esp.tagdict.models import Tag
from esp.themes import settings as themes_settings
from esp.themes.controllers import ThemeController

from esp.utils.web import render_to_response
from django.http import HttpResponseRedirect
from django.conf import settings

from datetime import datetime
import random
import string
import os.path
import shutil

THEME_ERROR_STRING = "Your site's theme is not in the generic templates system. " + \
                     "If you want to switch to one of the standard themes, " + \
                     "please contact the web team."

@admin_required
def landing(request):
    if settings.LOCAL_THEME:
        raise ESPError(THEME_ERROR_STRING, log=False)
    context = {}
    tc = ThemeController()
    context['theme_name'] = tc.get_current_theme()
    context['last_customization_name'] = tc.get_current_customization()
    context['has_header'] = os.path.exists(settings.MEDIA_ROOT + 'images/theme/header.png')
    return render_to_response('themes/landing.html', request, context)

@admin_required
def selector(request, keep_files=None):
    if settings.LOCAL_THEME:
        raise ESPError(THEME_ERROR_STRING, log=False)

    context = {}
    tc = ThemeController()

    if request.method == 'POST' and 'action' in request.POST:
        if request.POST['action'] == 'select':
            theme_name = request.POST['theme'].replace(' (current)', '')

            #   Check for differences between the theme's files and those in the working copy.
            #   If there are differences, require a confirmation from the user for each file.
            differences = tc.check_local_modifications(theme_name)
            if len(differences) > 0 and keep_files is None:
                return confirm_overwrite(request, current_theme=theme_name, differences=differences, orig_view='selector')

            #   Display configuration form if one is provided for the selected theme
            if tc.get_config_form_class(theme_name) is not None:
                return configure(request, current_theme=theme_name, force_display=True, keep_files=keep_files)

            tc.save_customizations('%s-last' % tc.get_current_theme())
            backup_info = tc.clear_theme(keep_files=keep_files)
            tc.load_theme(theme_name, backup_info=backup_info)

    context['theme_name'] = tc.get_current_theme()
    context['themes'] = tc.get_theme_names()
    return render_to_response('themes/selector.html', request, context)

@admin_required
def logos(request):
    context = {}
    tc = ThemeController()
    if not os.path.exists(settings.MEDIA_ROOT + 'images/backups'):
        os.makedirs(settings.MEDIA_ROOT + 'images/backups')

    if request.POST:
        if 'new_logo' in request.FILES:
            f = request.FILES['new_logo']
            # Overwrite existing logo file
            with open(settings.MEDIA_ROOT + 'images/theme/logo.png', 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            # Update logo version
            Tag.setTag("current_logo_version", value = hex(random.getrandbits(16)))
            # Backup the new logo file
            with open(settings.MEDIA_ROOT + 'images/backups/logo.' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.png', 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
        elif 'new_header' in request.FILES:
            f = request.FILES['new_header']
            # Overwrite existing header file
            with open(settings.MEDIA_ROOT + 'images/theme/header.png', 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            # Update header version
            Tag.setTag("current_header_version", value = hex(random.getrandbits(16)))
            # Backup the new header file
            with open(settings.MEDIA_ROOT + 'images/backups/header.' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.png', 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
        elif 'new_favicon' in request.FILES:
            f = request.FILES['new_favicon']
            # Overwrite existing logo file
            with open(settings.MEDIA_ROOT + 'images/favicon.ico', 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
            # Update favicon version
            Tag.setTag("current_favicon_version", value = hex(random.getrandbits(16)))
            # Backup the new favicon file
            with open(settings.MEDIA_ROOT + 'images/backups/favicon.' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.ico', 'wb+') as destination:
                for chunk in f.chunks():
                    destination.write(chunk)
        elif 'logo_select' in request.POST:
            # Overwrite existing logo file
            shutil.copyfile(settings.MEDIA_ROOT + 'images/backups/' + request.POST['logo_select'], settings.MEDIA_ROOT + 'images/theme/logo.png')
            # Update logo version
            Tag.setTag("current_logo_version", value = hex(random.getrandbits(16)))
        elif 'header_select' in request.POST:
            # Overwrite existing header file
            shutil.copyfile(settings.MEDIA_ROOT + 'images/backups/' + request.POST['header_select'], settings.MEDIA_ROOT + 'images/theme/header.png')
            # Update header version
            Tag.setTag("current_header_version", value = hex(random.getrandbits(16)))
        elif 'favicon_select' in request.POST:
            # Update favicon version
            shutil.copyfile(settings.MEDIA_ROOT + 'images/backups/' + request.POST['favicon_select'], settings.MEDIA_ROOT + 'images/favicon.ico')
            # Update favicon version
            Tag.setTag("current_favicon_version", value = hex(random.getrandbits(16)))

    context['logo_files'] = [(path.split('public')[1], path.split('images/backups/')[1]) for path in tc.list_filenames(settings.MEDIA_ROOT + 'images/backups', "logo\..*\.png")]
    context['header_files'] = [(path.split('public')[1], path.split('images/backups/')[1]) for path in tc.list_filenames(settings.MEDIA_ROOT + 'images/backups', "header\..*\.png")]
    context['favicon_files'] = [(path.split('public')[1], path.split('images/backups/')[1]) for path in tc.list_filenames(settings.MEDIA_ROOT + 'images/backups', "favicon\..*\.ico")]
    context['has_header'] = os.path.exists(settings.MEDIA_ROOT + 'images/theme/header.png')
    context['current_logo_version'] = Tag.getTag("current_logo_version")
    context['current_header_version'] = Tag.getTag("current_header_version")
    context['current_favicon_version'] = Tag.getTag("current_favicon_version")

    return render_to_response('themes/logos.html', request, context)

@admin_required
def confirm_overwrite(request, current_theme=None, differences=None, orig_view=None):
    """ Display a form asking the user which local modified files
        they would like to keep, and which they would like to overwrite
        with the ones from the theme data.  """

    if settings.LOCAL_THEME:
        raise ESPError(THEME_ERROR_STRING, log=False)

    context = {}
    tc = ThemeController()

    if current_theme is None:
        current_theme = request.POST.get('theme', '')

    if request.method == 'POST' and request.POST.get('confirm_overwrite', '0') == '1':
        files_to_keep = []
        diffs_current = tc.check_local_modifications(current_theme)

        #   Build a list of filenames that we are not supposed to overwrite.
        for entry in diffs_current:
            post_key = 'overwrite_%s' % entry['filename_hash']
            post_val = request.POST.get(post_key, None)
            if post_val is not None:
                if post_val != 'overwrite':
                    files_to_keep.append(entry['filename'])

        #   Continue with the original view (typically the theme selector).
        view_func = selector
        if request.POST.get('orig_view', '') == 'recompile':
            view_func = recompile
        return view_func(request, keep_files=files_to_keep)

    #   Display the form asking the user which files to keep/overwrite.
    if differences is None:
        differences = tc.check_local_modifications(current_theme)

    context['theme_name'] = current_theme
    context['differences'] = differences
    context['orig_view'] = orig_view
    return render_to_response('themes/confirm_overwrite.html', request, context)

@admin_required
def configure(request, current_theme=None, force_display=False, keep_files=None):
    if settings.LOCAL_THEME:
        raise ESPError(THEME_ERROR_STRING, log=False)

    context = {}
    tc = ThemeController()
    if current_theme is None:
        current_theme = request.POST.get('theme', None) or tc.get_current_theme()
    context['theme_name'] = current_theme

    form_class = tc.get_config_form_class(current_theme)
    if form_class is None:
        form = None
        return render_to_response('themes/configure_form.html', request, context)

    if request.method == 'POST' and not force_display:
        form = form_class(request.POST.copy())

        if form.is_valid():
            #   Done; save results and go back to landing page.
            if form.cleaned_data['theme'] != tc.get_current_theme():
                tc.save_customizations('%s-last' % tc.get_current_theme())

            if form.cleaned_data['just_selected']:
                #   Detect which files (in the active media directories) are being preserved,
                #   and use this information when reloading the theme.
                keep_files = request.POST.getlist('keep_files', [])
                backup_info = tc.clear_theme(keep_files=keep_files)
                tc.load_theme(form.cleaned_data['theme'], backup_info=backup_info)

            form.save_to_tag()
            return HttpResponseRedirect('/themes/')
    else:
        form = form_class.load_from_tag(theme_name=current_theme, just_selected=force_display)

    context['form'] = form
    context['keep_files'] = keep_files
    context['confirm_overwrite'] = request.POST.get('confirm_overwrite', '0')

    return render_to_response('themes/configure_form.html', request, context)

@admin_required
def editor(request):
    if settings.LOCAL_THEME:
        raise ESPError(THEME_ERROR_STRING, log=False)

    tc = ThemeController()

    if request.method == 'POST':
        #   Handle form submission
        vars = None
        palette = None

        if 'save' in request.POST:
            if request.POST['saveThemeName'] == '':
                theme_name = tc.get_current_customization()
                if theme_name == 'None':
                    #   Generate a temporary theme name
                    random_slug  = ''.join(random.choice(string.ascii_lowercase) for i in range(4))
                    theme_name = 'theme-%s-%s' % (datetime.now().strftime('%Y%m%d'), random_slug)
            else:
                theme_name = request.POST['saveThemeName']
            vars = request.POST.dict()
            palette = request.POST.getlist('palette')
            tc.save_customizations(theme_name, vars=vars, palette=palette)
            tc.set_current_customization(theme_name)
        elif 'load' in request.POST:
            (vars, palette) = tc.load_customizations(request.POST['loadThemeName'])
        elif 'delete' in request.POST:
            tc.delete_customizations(request.POST['loadThemeName'])
        elif 'apply' in request.POST:
            vars = request.POST.dict()
            palette = request.POST.getlist('palette')

        #   Re-generate the CSS for the current theme given the supplied settings
        if vars:
            tc.customize_theme(vars)
        if palette is not None:
            tc.set_palette(palette)

    #   Get current theme and customization settings
    current_theme = tc.get_current_theme()
    context = tc.find_less_variables(flat=True)
    context.update(tc.get_current_params())
    context['palette'] = tc.get_palette()
    context['theme_name'] = current_theme

    #   Get list of available customizations
    context['available_themes'] = tc.get_customization_names()
    context['last_used_setting'] = tc.get_current_customization()

    #   Load a bunch of preset fonts
    context['sans_fonts'] = six.iteritems(themes_settings.sans_serif_fonts)

    #   Load the theme-specific options
    adv_vars = tc.find_less_variables(current_theme, theme_only=True)
    context['adv_vars'] = {}
    for filename in adv_vars:
        category_name = os.path.basename(filename)[:-5]
        category_vars = []
        keys = sorted(adv_vars[filename].keys())
        for key in keys:
            #   Detect type of variable based on default value
            initial_val = adv_vars[filename][key]
            if key in context:
                initial_val = context[key]
            if initial_val.startswith('#'):
                category_vars.append((key, 'color', initial_val))
            elif 'color' in key:
                #   This is a nontrivial color value.  However, we only allow overriding
                #   these variables with specific colors.
                category_vars.append((key, 'color', ''))
            elif initial_val.endswith('px') or initial_val.endswith('em'):
                category_vars.append((key, 'length', initial_val))
            else:
                category_vars.append((key, 'text', initial_val))
        context['adv_vars'][category_name] = category_vars
    context['variable_defaults'] = tc.get_variable_defaults(current_theme)

    return render_to_response('themes/editor.html', request, context)

@admin_required
def recompile(request, keep_files=None):
    if settings.LOCAL_THEME:
        raise ESPError(THEME_ERROR_STRING, log=False)

    tc = ThemeController()

    #   Check for differences between the theme's files and those in the working copy.
    #   If there are differences, require a confirmation from the user for each file.
    theme_name = tc.get_current_theme()
    differences = tc.check_local_modifications(theme_name)
    if len(differences) > 0 and keep_files is None:
        return confirm_overwrite(request, current_theme=theme_name, differences=differences, orig_view='recompile')

    tc.recompile_theme(keep_files=keep_files)
    return HttpResponseRedirect('/themes/')

