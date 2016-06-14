
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

import datetime
import logging
logger = logging.getLogger(__name__)
import os
import os.path
import shutil
import re
import subprocess
import tempfile
import distutils.dir_util
import json
import hashlib

from django.conf import settings
from django.template.loader import render_to_string

from esp.utils.models import TemplateOverride
from esp.utils.template import Loader as TemplateOverrideLoader
from esp.tagdict.models import Tag
from esp.themes import settings as themes_settings
from esp.varnish import varnish
from esp.middleware import ESPError

THEME_PATH = os.path.join(settings.PROJECT_ROOT, 'esp', 'themes', 'theme_data')

class ThemeController(object):
    """
    This is a controller for manipulating the currently selected theme.
    """
    def __init__(self, *args, **kwargs):
        self.css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)

    def get_current_theme(self):
        return Tag.getTag('current_theme_name', default='default')

    def get_current_customization(self):
        return Tag.getTag('prev_theme_customization', default='None')

    def set_current_customization(self, theme_name):
        Tag.setTag('prev_theme_customization', value=theme_name)

    def unset_current_customization(self):
        Tag.unSetTag('prev_theme_customization')

    def get_current_params(self):
        return json.loads(Tag.getTag('current_theme_params', default='{}'))

    def get_theme_names(self):
        return [name for name in os.listdir(THEME_PATH)
            if os.path.isdir(os.path.join(THEME_PATH, name))]

    def get_template_settings(self):
        """
        Get the current template settings. The base settings are the initial
        values of the configuration form fields, which are overriden by values
        in the theme_template_control Tag.
        """
        form_class = self.get_config_form_class(self.get_current_theme())
        if form_class is not None:
            data = form_class.initial_data()
        else:
            data = {}
        data.update(json.loads(Tag.getTag('theme_template_control', default='{}')))
        data['theme_name'] = self.get_current_theme()
        return data

    def set_template_settings(self, data):
        #   Merge with the existing settings so you don't forget anything
        initial_data = self.get_template_settings()
        initial_data.update(data)
        now = datetime.datetime.now()
        mtime = {'year': now.year, 'month': now.month, 'day': now.day,
                 'hour': now.hour, 'minute': now.minute,
                 'second': now.second, 'microsecond': now.microsecond}
        initial_data.update({'mtime': mtime})
        Tag.setTag('theme_template_control', value=json.dumps(initial_data))

    def update_template_settings(self):
        """
        Refreshes the template settings, possibly updating some values (such as
        the mtime).
        """
        self.set_template_settings(self.get_template_settings())

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
            result.append(os.path.join(themes_settings.less_dir, 'variables_custom.less'))
            result.append(os.path.join(themes_settings.less_dir, 'main.less'))
        #   Make sure variables.less is included first, before any other custom LESS code
        result += self.list_filenames(os.path.join(self.base_dir(theme_name), 'less'), r'variables(.*?)\.less')
        result += self.list_filenames(os.path.join(self.base_dir(theme_name), 'less'), r'(?<!variables)\.less$')
        return result

    def find_less_variables(self, theme_name=None, theme_only=False, flat=False):
        if theme_name is None:
            theme_name = self.get_current_theme()

        #   Return value is a mapping of names to default values (both strings)
        results = {}
        for filename in self.get_less_names(theme_name, theme_only=theme_only):
            local_results = {}

            logger.debug('find_less_variables: including file %s', filename)

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
        #   Hack to make things work on Windows systems
        INCLUDE_PATH_SEP = ':'
        if os.name == 'nt':
            INCLUDE_PATH_SEP = ';'

        #   Load LESS files in order of search path
        less_data = ''
        for filename in self.get_less_names(theme_name):
            less_file = open(filename)
            logger.debug('Including LESS source %s', filename)
            less_data += '\n' + less_file.read()
            less_file.close()

        if themes_settings.THEME_DEBUG:
            # TODO(benkraft): should this and its friend below get removed now?
            # I think they're the last users of THEME_DEBUG.
            tf1 = open('debug_1.less', 'w')
            tf1.write(less_data)
            tf1.close()

        #   Make icon image path load from the CDN by default
        if 'iconSpritePath' not in variable_data:
            variable_data['iconSpritePath'] = '"%s/bootstrap/img/glyphicons-halflings.png"' % settings.CDN_ADDRESS

        #   Replace all variable declarations for which we have a value defined
        for (variable_name, variable_value) in variable_data.iteritems():
            less_data = re.sub(r'@%s:(\s*)(.*?);' % variable_name, r'@%s: %s;' % (variable_name, variable_value), less_data)

        if themes_settings.THEME_DEBUG:
            tf1 = open('debug_2.less', 'w')
            tf1.write(less_data)
            tf1.close()

        less_search_path = INCLUDE_PATH_SEP.join(settings.LESS_SEARCH_PATH + [os.path.join(settings.MEDIA_ROOT, 'theme_editor', 'less')])
        logger.debug('LESS search path is "%s"', less_search_path)

        #   Compile to CSS
        lessc_args = ['lessc', '--include-path="%s"' % less_search_path, '-']
        lessc_process = subprocess.Popen(' '.join(lessc_args), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        css_data = lessc_process.communicate(less_data)[0]

        if lessc_process.returncode != 0:
            raise ESPError('The stylesheet compiler (lessc) returned error code %d.  Please check the LESS sources and settings you are using to generate the theme, or if you are using a provided theme please contact the <a href="mailto:%s">Web support team</a>.<br />LESS compile command was: <pre>%s</pre>' % (lessc_process.returncode, settings.DEFAULT_EMAIL_ADDRESSES['support'], ' '.join(lessc_args)), log=True)

        output_file = open(output_filename, 'w')
        output_file.write(css_data)
        output_file.close()
        logger.debug('Wrote %.1f KB CSS output to %s', len(css_data) / 1000., output_filename)

    def recompile_theme(self, theme_name=None, customization_name=None, keep_files=None):
        """
        Reloads the theme (possibly updating the template overrides with recent
        code changes), then recompiles the customizations.
        """
        if settings.LOCAL_THEME:
            return
        if (customization_name is None) or (customization_name == "None"):
            customization_name = self.get_current_customization()
        if customization_name == "None":
            return
        if theme_name is None:
            theme_name = self.get_current_theme()
        backup_info = self.clear_theme(keep_files=keep_files)
        self.load_theme(theme_name, backup_info=backup_info)
        self.update_template_settings()
        (vars, palette) = self.load_customizations(customization_name)
        if vars:
            self.customize_theme(vars)
        if palette:
            self.set_palette(palette)

    def backup_files(self, dir, keep_files=None):
        """ Copy the files specified in keep_files (relative to directory dir)
            to temporary locations and return a tuple of
            (filename, temporary_location) pairs.   """

        backup_info = []

        if keep_files is None:
            #   The default behavior, with keep_files = None, is to back up all
            #   files that differ between the working copy and the current theme.
            modifications = self.check_local_modifications(self.get_current_theme())
            keep_files = [item['filename'] for item in modifications]

        for filename in keep_files:
            full_filename = os.path.join(dir, filename)
            (file_desc, file_path) = tempfile.mkstemp()
            file_obj = os.fdopen(file_desc, 'wb')
            file_obj.write(open(full_filename, 'rb').read())
            file_obj.close()
            backup_info.append((filename, file_path))
        return backup_info

    def restore_files(self, dir, backup_info):
        """ Restore files from the temporary locations provided by the
            backup_files() function above.  """

        for (filename, file_path) in backup_info:
            shutil.copy(file_path, os.path.join(dir, filename))
            os.remove(file_path)

    def clear_theme(self, theme_name=None, keep_files=None):

        if theme_name is None:
            theme_name = self.get_current_theme()

        #   Remove template overrides matching the theme name
        logger.debug('Clearing theme: %s', theme_name)
        for template_name in self.get_template_names(theme_name):
            TemplateOverride.objects.filter(name=template_name).delete()
            logger.debug('-- Removed template override: %s', template_name)

        #   Clear template override cache
        TemplateOverrideLoader.get_template_hash.delete_all()

        #   If files are to be preserved, copy them to temporary locations
        #   and return a record of those locations (backup_info).
        #   This is much easier than writing new functions for removing and
        #   copying directory trees.
        backup_info = self.backup_files(settings.MEDIA_ROOT, keep_files)
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
        self.unset_current_customization()

        #   Clear the Varnish cache
        varnish.purge_all()

        return backup_info

    def get_file_summaries(self, dir):
        """ Retrieve a list of (filename, size, hash of contents) tuples.
            For comparing the state of directories that are copied
            from the theme data.    """

        result = []
        for filename in os.listdir(dir):
            full_filename = os.path.join(dir, filename)
            if os.path.isdir(filename):
                result += self.get_file_summaries(full_filename)
            else:
                file_data = open(full_filename, 'rb').read()
                result.append((full_filename, os.path.getsize(full_filename), hashlib.sha1(file_data).hexdigest()))
        return result

    def get_directory_differences(self, src_dir, dest_dir):
        """ Retrieve a list of relative paths that exist in both src_dir
            and dest_dir but with different file contents.  """

        differences = []
        summaries_src = self.get_file_summaries(src_dir)
        summaries_dest = self.get_file_summaries(dest_dir)

        #   Build an index of the source files.
        index_src = {}
        for (filename, filesize, hash) in summaries_src:
            rel_filename_src = os.path.relpath(filename, src_dir)
            index_src[rel_filename_src] = (filesize, hash)

        #   Iterate over destination files and see which ones match.
        #   Compare the hashes of those files.
        for (filename, filesize_dest, hash_dest) in summaries_dest:
            rel_filename_dest = os.path.relpath(filename, dest_dir)
            if rel_filename_dest in index_src:
                (filesize_src, hash_src) = index_src[rel_filename_dest]
                if hash_src != hash_dest:
                    differences.append({
                        'filename': rel_filename_dest,
                        'filename_hash': hashlib.sha1(rel_filename_dest).hexdigest(),
                        'source_size': filesize_src,
                        'dest_size': filesize_dest,
                    })

        return differences

    def check_local_modifications(self, theme_name):
        """ Return a list of relative paths under /media that could be
            to be overwritten by loading the specified theme.   """
        differences = []

        img_src_dir = os.path.join(self.base_dir(theme_name), 'images')
        if os.path.exists(img_src_dir):
            img_dest_dir = os.path.join(settings.MEDIA_ROOT, 'images', 'theme')
            if not os.path.exists(img_dest_dir):
                os.mkdir(img_dest_dir)
            for diff_item in self.get_directory_differences(img_src_dir, img_dest_dir):
                diff_item['filename'] = os.path.join('images', 'theme', diff_item['filename'])
                diff_item['dest_url'] = os.path.join('/media', diff_item['filename'])
                differences.append(diff_item)

        script_src_dir = os.path.join(self.base_dir(theme_name), 'scripts')
        if os.path.exists(script_src_dir):
            script_dest_dir = os.path.join(settings.MEDIA_ROOT, 'scripts', 'theme')
            if not os.path.exists(script_dest_dir):
                os.mkdir(script_dest_dir)
            for diff_item in self.get_directory_differences(script_src_dir, script_dest_dir):
                diff_item['filename'] = os.path.join('scripts', 'theme', diff_item['filename'])
                diff_item['dest_url'] = os.path.join('/media', diff_item['filename'])
                differences.append(diff_item)

        return differences

    def load_theme(self, theme_name, **kwargs):

        #   Create template overrides using data provided (our models handle versioning)
        logger.debug('Loading theme: %s', theme_name)
        for template_name in self.get_template_names(theme_name):
            #   Read default template override contents provided by theme
            to = TemplateOverride(name=template_name)
            template_filename = os.path.join(self.base_dir(theme_name), 'templates', template_name)
            template_file = open(template_filename, 'r')
            to.content = template_file.read()

            #   Add a Django template comment tag indicating theme type to the main.html override (for tests)
            if to.name == 'main.html':
                to.content += ('\n{%% comment %%} Theme: %s {%% endcomment %%}\n' % theme_name)

            to.save()
            logger.debug('-- Created template override: %s', template_name)

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

        #   If files need to be restored, copy them back to the desired locations.
        if kwargs.get('backup_info', None) is not None:
            self.restore_files(settings.MEDIA_ROOT, kwargs['backup_info'])

        Tag.setTag('current_theme_name', value=theme_name)
        Tag.setTag('current_theme_params', value='{}')
        Tag.unSetTag('current_theme_palette')
        self.unset_current_customization()

        #   Clear the Varnish cache
        varnish.purge_all()

    def customize_theme(self, vars):
        logger.debug('Customizing theme with variables: %s', vars)
        self.compile_css(self.get_current_theme(), vars, self.css_filename)
        vars_available = self.find_less_variables(self.get_current_theme(), flat=True)
        vars_diff = {}
        for key in vars:
            if key in vars_available and len(vars[key].strip()) > 0 and vars[key] != vars_available[key]:
                logger.debug('Customizing: %s -> %s', key, vars[key])
                vars_diff[key] = vars[key]
        logger.debug('Customized %d variables for theme %s', len(vars_diff), self.get_current_theme())
        Tag.setTag('current_theme_params', value=json.dumps(vars_diff))

        #   Clear the Varnish cache
        varnish.purge_all()

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

        self.set_current_customization(save_name)

        logger.debug("vars: %s", vars)
        logger.debug("palette: %s", palette)
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
        palette_base = json.loads(Tag.getTag('current_theme_palette', default='[]'))

        #   Augment with the colors from any global LESS variables
        palette = set(palette_base)
        base_vars = self.find_less_variables()
        for varset in base_vars.values():
            for val in varset.values():
                if isinstance(val, basestring) and val.startswith('#'):
                    palette.add(val)

        palette = list(palette)
        palette.sort()
        return palette

    def set_palette(self, palette):
        Tag.setTag('current_theme_palette', value=json.dumps(palette))
