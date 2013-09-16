
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

from esp.utils.models import TemplateOverride
from esp.utils.template import Loader as TemplateOverrideLoader
from esp.tagdict.models import Tag
from esp.themes import settings as themes_settings

from django.conf import settings
from django.template.loader import render_to_string

from string import Template
import cStringIO
import os
import re
import subprocess
import tempfile
import distutils.dir_util
import simplejson as json

THEME_PATH = os.path.join(settings.PROJECT_ROOT, 'esp', 'themes', 'theme_data')


class ThemeController(object):
    """
    This is a controller for manipulating the currently selected theme.
    """
    def __init__(self, *args, **kwargs):
        self.css_filename = os.path.join(settings.MEDIA_ROOT, 'styles/theme_compiled.css')
        
    def get_current_theme(self):
        return Tag.getTag('current_theme_name', default='default')
        
    def get_current_params(self):
        return json.loads(Tag.getTag('current_theme_params', default='{}'))

    def get_theme_names(self):
        return [name for name in os.listdir(THEME_PATH)
            if os.path.isdir(os.path.join(THEME_PATH, name))]

    def get_template_settings(self):
        return json.loads(Tag.getTag('theme_template_control', default='{}'))

    def set_template_settings(self, data):
        #   Merge with the existing settings so you don't forget anything
        initial_data = self.get_template_settings()
        initial_data.update(data)
        Tag.setTag('theme_template_control', value=json.dumps(initial_data))

    def base_dir(self, theme_name):
        return os.path.join(THEME_PATH, theme_name)

    def list_filenames(self, dir, file_regexp, mask_base=False):
        """ Quick search for files in the specified directory (dir) which match
            the specified pattern (file_regexp).  Used to determine which
            templates and LESS files are present in a given theme. """
        result = []
        bd_len = len(dir)
        for dirpath, dirnames, filenames in os.walk(dir):
            for filename in filenames:
                if re.search(file_regexp, filename):
                    if mask_base:
                        full_name = ('%s/%s' % (dirpath[bd_len:], filename))[1:]
                    else:
                        full_name = dirpath + '/' + filename
                    #   Hack needed for Windows - may not be necessary for other OS
                    result.append(full_name.replace('\\', '/'))
        return result
        
    def get_template_names(self, theme_name):
        return self.list_filenames(self.base_dir(theme_name) + '/templates', r'\.html$', mask_base=True)

    def get_config_form_class(self, theme_name):
        """ Themes can define a form for configuring settings that are not
            represented by LESS variables.  This function will retrieve that
            form class if the theme has defined one. """
        #   There are two steps; if either fails, we return None and the form is skipped.
        #   Step 1: Try to get the Python module containing the form class.
        try:
            theme_form_module = __import__('esp.themes.theme_data.%s.config_form' % theme_name, (), (), 'ConfigForm')
        except ImportError:
            return None
        #   Step 2: Try to get the form class from the module.
        if hasattr(theme_form_module, 'ConfigForm'):
            return theme_form_module.ConfigForm
        else:
            return None

    def global_less(self, search_dirs=None):
        if search_dirs is None:
            search_dirs = settings.LESS_SEARCH_PATH
        result = []
        for dir in search_dirs:
            result += self.list_filenames(dir, r'\.less$')
        return result
        
    def get_less_names(self, theme_name, theme_only=False):
        result = []
        if not theme_only:
            result += self.global_less()
            result.append(os.path.join(themes_settings.less_dir, 'bootstrap.less'))
        #   Make sure variables.less is included first, before any other custom LESS code
        result += self.list_filenames(os.path.join(self.base_dir(theme_name), 'less'), r'variables\.less')
        result += self.list_filenames(os.path.join(self.base_dir(theme_name), 'less'), r'(?<!variables)\.less$')
        return result
        
    def find_less_variables(self, theme_name=None, theme_only=False, flat=False):
        if theme_name is None:
            theme_name = self.get_current_theme()

        #   Return value is a mapping of names to default values (both strings)
        results = {}
        for filename in self.get_less_names(theme_name, theme_only=theme_only):
            local_results = {}
        
            #   Read less file
            less_file = open(filename)
            less_data = less_file.read()
            less_file.close()

            #   Find variable declarations
            for item in re.findall(r'@([a-zA-Z0-9_]+):\s*(.*?);', less_data):
                local_results[item[0]] = item[1]

            if flat:
                #   Store all variables in same dictionary if 'flat' mode is requested
                results.update(local_results)
            else:
                #   Store in a dictionary based on filename so we know where they came from
                results[filename] = local_results

        return results
        
    def compile_css(self, theme_name, variable_data, output_filename):
        #   Load LESS files in order of search path
        less_data = ''
        for filename in self.get_less_names(theme_name):
            less_file = open(filename)
            if themes_settings.THEME_DEBUG: print 'Including LESS source %s' % filename
            less_data += '\n' + less_file.read()
            less_file.close()

        if themes_settings.THEME_DEBUG:
            tf1 = open('debug_1.less', 'w')
            tf1.write(less_data)
            tf1.close()

        #   Make icon image path load from the CDN by default
        if 'iconSpritePath' not in variable_data:
            variable_data['iconSpritePath'] = '"%s/bootstrap/img/glyphicons-halflings.png"' % settings.CDN_ADDRESS

        #   Replace all variable declarations for which we have a value defined
        for (variable_name, variable_value) in variable_data.iteritems():
            less_data = re.sub(r'@%s:(\s*)(.*?);' % variable_name, r'@%s: %s;' % (variable_name, variable_value), less_data)
            #   print '  Substituted value %s = %s' % (variable_name, variable_value)

        if themes_settings.THEME_DEBUG:
            tf1 = open('debug_2.less', 'w')
            tf1.write(less_data)
            tf1.close()

        (less_output_fd, less_output_filename) = tempfile.mkstemp()
        less_output_file = os.fdopen(less_output_fd, 'w')
        less_output_file.write(less_data)
        if themes_settings.THEME_DEBUG: print 'Wrote %d bytes to LESS file %s' % (len(less_data), less_output_filename)
        less_output_file.close()

        less_search_path = ', '.join([("'%s'" % dirname) for dirname in (settings.LESS_SEARCH_PATH + [os.path.join(settings.MEDIA_ROOT, 'theme_editor', 'less')])])
	if themes_settings.THEME_DEBUG: print 'LESS search path is "%s"' % less_search_path

        minify_js = False
        js_code = Template("""
var fs = require('fs');
var less = require('less');

var parser = new(less.Parser)({
    paths: [$lesspath], // Specify search paths for @import directives
    filename: 'theme_compiled.less' // Specify a filename, for better error messages
});

var data = fs.readFileSync('$lessfile', 'utf8');

parser.parse(data, function (err, tree) {
    if (err)
    {
        return console.error(err);
    }
    console.log(tree.toCSS({ compress: $minify })); // Minify CSS output if desired
});
        """).substitute(lesspath=less_search_path, lessfile=less_output_filename.replace('\\', '/'), minify=str(minify_js).lower())

        #   print js_code

        #   Compile to CSS
        lessc_args = ["node"]
        lessc_process = subprocess.Popen(lessc_args, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        css_data = lessc_process.communicate(input=js_code)[0]

        output_file = open(output_filename, 'w')
        output_file.write(css_data)
        output_file.close()
        if themes_settings.THEME_DEBUG: print 'Wrote %.1f KB CSS output to %s' % (len(css_data) / 1000., output_filename)

    def clear_theme(self, theme_name=None):
    
        if theme_name is None:
            theme_name = self.get_current_theme()
        
        #   Remove template overrides matching the theme name
        if themes_settings.THEME_DEBUG: print 'Clearing theme: %s' % theme_name
        for template_name in self.get_template_names(theme_name):
            TemplateOverride.objects.filter(name=template_name).delete()
            if themes_settings.THEME_DEBUG: print '-- Removed template override: %s' % template_name

        #   Clear template override cache
        TemplateOverrideLoader.get_template_hash.delete_all()

        #   Remove images and script files from the active theme directory
        if os.path.exists(settings.MEDIA_ROOT + 'images/theme'):
            distutils.dir_util.remove_tree(settings.MEDIA_ROOT + 'images/theme')
        if os.path.exists(settings.MEDIA_ROOT + 'scripts/theme'):
            distutils.dir_util.remove_tree(settings.MEDIA_ROOT + 'scripts/theme')

        #   Remove compiled CSS file
        if os.path.exists(self.css_filename):
            os.remove(self.css_filename)

        Tag.unSetTag('current_theme_name')
        Tag.unSetTag('current_theme_params')
        Tag.unSetTag('current_theme_palette')
        Tag.unSetTag('prev_theme_customization')

    def load_theme(self, theme_name, **kwargs):
    
        #   Create template overrides using data provided (our models handle versioning)
        if themes_settings.THEME_DEBUG: print 'Loading theme: %s' % theme_name
        for template_name in self.get_template_names(theme_name):
            #   Read default template override contents provided by theme
            to = TemplateOverride(name=template_name)
            template_filename = os.path.join(self.base_dir(theme_name), 'templates', template_name)
            template_file = open(template_filename, 'r')
            to.content = template_file.read()
            #   print 'Template override %s contents: \n%s' % (to.name, to.content)
            to.save()
            if themes_settings.THEME_DEBUG: print '-- Created template override: %s' % template_name

        #   Clear template override cache
        TemplateOverrideLoader.get_template_hash.delete_all()

        #   Collect LESS files from appropriate sources and compile CSS
        self.compile_css(theme_name, {}, self.css_filename)
        
        #   Copy images and script files to the active theme directory
        img_src_dir = os.path.join(self.base_dir(theme_name), 'images')
        if os.path.exists(img_src_dir):
            img_dest_dir = os.path.join(settings.MEDIA_ROOT, 'images', 'theme')
            distutils.dir_util.copy_tree(img_src_dir, img_dest_dir)
        script_src_dir = os.path.join(self.base_dir(theme_name), 'scripts')
        if os.path.exists(script_src_dir):
            script_dest_dir = os.path.join(settings.MEDIA_ROOT, 'scripts', 'theme')
            distutils.dir_util.copy_tree(script_src_dir, script_dest_dir)

        Tag.setTag('current_theme_name', value=theme_name)
        Tag.setTag('current_theme_params', value='{}')
        Tag.unSetTag('current_theme_palette')
        Tag.unSetTag('prev_theme_customization')

    def customize_theme(self, vars):
        self.compile_css(self.get_current_theme(), vars, self.css_filename)
        vars_available = self.find_less_variables(self.get_current_theme(), flat=True)
        vars_diff = {}
        for key in vars:
            if key in vars_available and len(vars[key].strip()) > 0 and vars[key] != vars_available[key]:
                print 'Customizing: %s -> %s' % (key, vars[key])
                vars_diff[key] = vars[key]
        if themes_settings.THEME_DEBUG: print 'Customized %d variables for theme %s' % (len(vars_diff), self.get_current_theme())
        Tag.setTag('current_theme_params', value=json.dumps(vars_diff))

    ##  Customizations - stored as LESS files with modified variables only; palette is included

    def save_customizations(self, save_name, theme_name=None, vars=None, palette=None):
        if theme_name is None:
            theme_name = self.get_current_theme()
        if vars is None:
            vars = self.get_current_params()
        if palette is None:
            palette = self.get_palette()

        vars_orig = self.find_less_variables(theme_name, flat=True)
        for key in vars.keys():
            if key not in vars_orig:
                del vars[key]

        context = {}
        context['vars'] = vars
        context['base_theme'] = theme_name
        context['save_name'] = save_name
        context['palette'] = palette

        f = open(os.path.join(themes_settings.themes_dir, '%s.less' % save_name), 'w')
        f.write(render_to_string('themes/custom_vars.less', context))
        f.close()

    def load_customizations(self, save_name):

        f = open(os.path.join(themes_settings.themes_dir, '%s.less' % save_name), 'r')
        data = f.read()
        f.close()

        #   Collect LESS variables
        vars = {}
        for match in re.findall(r'@(\w+):\s*(.*?);', data):
            vars[match[0]] = match[1]

        #   Collect save name stored in file
        save_name_match = re.search(r'// Theme Name: (.+?)\n', data)
        if save_name_match:
            assert(save_name == save_name_match.group(1))

        #   Collect palette
        palette = []
        for match in re.findall(r'palette:(#?\w+?);', data):
            palette.append(match)

        print (vars, palette)
        return (vars, palette)
        
    def delete_customizations(self, save_name):
        os.remove(os.path.join(themes_settings.themes_dir, '%s.less' % save_name))

    def get_customization_names(self):
        result = []
        filenames = os.listdir(os.path.join(themes_settings.themes_dir))
        for fn in filenames:
            if fn.endswith('.less'):
                result.append(fn[:-5])
        return result

    ##  Palette getter/setter -- palette is a list of strings which each contain
    ##  HTML color codes, e.g. ["#FFFFFF", "#3366CC"]

    def get_palette(self):
        return json.loads(Tag.getTag('current_theme_palette', default='[]'))

    def set_palette(self, palette):
        Tag.setTag('current_theme_palette', value=json.dumps(palette))
