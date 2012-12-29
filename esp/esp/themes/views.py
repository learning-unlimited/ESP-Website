
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
  Email: web-team@lists.learningu.org
"""

from esp.users.models import admin_required
from esp.tagdict.models import Tag
from esp.themes import settings as themes_settings
from esp.themes.controllers import ThemeController

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from datetime import datetime
import random
import string
import os.path

@admin_required
def editor(request):

    tc = ThemeController()
    
    if request.method == 'POST':
        #   Handle form submission
        vars = None
        palette = None

        if 'save' in request.POST:
            if request.POST['saveThemeName'] == '':
                theme_name = Tag.getTag('prev_theme_customization', default='None')
                if theme_name == 'None':
                    #   Generate a temporary theme name
                    random_slug  = ''.join(random.choice(string.lowercase) for i in range(4))
                    theme_name = 'theme-%s-%s' % (datetime.now().strftime('%Y%m%d'), random_slug)
            else:
                theme_name = request.POST['saveThemeName']
            vars = request.POST.dict()
            palette = request.POST.getlist('palette')
            tc.save_customizations(theme_name, vars=vars, palette=palette)
            Tag.setTag('prev_theme_customization', value=theme_name)
        elif 'load' in request.POST:
            (vars, palette) = tc.load_customizations(request.POST['loadThemeName'])
            Tag.setTag('prev_theme_customization', value=request.POST['loadThemeName'])
        elif 'delete' in request.POST:
            tc.delete_customizations(request.POST['loadThemeName'])
        elif 'apply' in request.POST:
            vars = request.POST.dict()
            palette = request.POST.getlist('palette')

        #   Re-generate the CSS for the current theme given the supplied settings
        if vars:
            tc.customize_theme(vars)
        if palette:
            tc.set_palette(palette)

    #   Get current theme and customization settings
    current_theme = tc.get_current_theme()
    context = tc.find_less_variables(flat=True)
    context.update(tc.get_current_params())
    context['palette'] = tc.get_palette()

    #   Get list of available customizations
    context['available_themes'] = tc.get_customization_names()
    context['last_used_setting'] = Tag.getTag('prev_theme_customization', default='None')

    #   Load a bunch of preset fonts
    context['sans_fonts'] = sorted(themes_settings.sans_serif_fonts.iteritems())
    
    #   Load the theme-specific options
    adv_vars = tc.find_less_variables(current_theme, theme_only=True)
    context['adv_vars'] = {}
    for filename in adv_vars:
        category_name = os.path.basename(filename)[:-5]
        category_vars = {}
        for key in adv_vars[filename]:
            #   Detect type of variable based on default value
            initial_val = adv_vars[filename][key]
            if key in context:
                initial_val = context[key]
            if initial_val.startswith('#'):
                category_vars[key] = ('color', initial_val)
            elif initial_val.endswith('px') or initial_val.endswith('em'):
                category_vars[key] = ('length', initial_val)
            else:
                category_vars[key] = ('text', initial_val)
        context['adv_vars'][category_name] = category_vars

    return render_to_response('themes/editor.html', context, context_instance=RequestContext(request))

