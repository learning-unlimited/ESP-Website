
from io import open
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
import random
import re
import subprocess
import tempfile
import textwrap
import json
import hashlib
import copy
from urllib.parse import quote, unquote

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.template.loader import render_to_string

from esp.utils.models import TemplateOverride
from esp.utils.template import Loader as TemplateOverrideLoader
from esp.tagdict.models import Tag
from esp.themes import settings as themes_settings
from esp.varnish import varnish
from esp.middleware import ESPError

THEME_PATH = os.path.join(settings.PROJECT_ROOT, 'esp', 'themes', 'theme_data')

def _detect_scss_themes():
    """Discover which theme directories contain a scss/ subdirectory.

    Called once at module import time — not with user input — so the
    resulting frozenset is a trusted constant.  has_scss() does a simple
    membership check against it, avoiding any path expression that touches
    user-supplied data.
    """
    try:
        return frozenset(
            name for name in os.listdir(THEME_PATH)
            if os.path.isdir(os.path.join(THEME_PATH, name, 'scss'))
        )
    except OSError:
        return frozenset()

_SCSS_THEMES = _detect_scss_themes()

# Pre-computed map from theme name → scss/ directory path, built at import time
# from _SCSS_THEMES so get_scss_names can look up the directory by name without
# using the (potentially user-supplied) theme_name in an os.path.join expression.
_SCSS_THEME_DIRS = {name: os.path.join(THEME_PATH, name, 'scss') for name in _SCSS_THEMES}

def _detect_all_themes():
    """All theme directory names — computed at import time, not from user input."""
    try:
        return frozenset(
            name for name in os.listdir(THEME_PATH)
            if os.path.isdir(os.path.join(THEME_PATH, name))
            and name != '__pycache__'
        )
    except OSError:
        return frozenset()

_ALL_THEMES = _detect_all_themes()

def _get_theme_editor_dir():
    """Return the realpath of the theme_editor directory, validated to be inside MEDIA_ROOT.

    Computed once at import time from server-configured settings, not from any
    user-supplied request data, so the result is a trusted constant.
    """
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    resolved = os.path.realpath(os.path.join(media_root, 'theme_editor'))
    if not resolved.startswith(media_root + os.sep) and resolved != media_root:
        raise ValueError('theme_editor_dir path is outside MEDIA_ROOT')
    return resolved

_THEME_EDITOR_DIR = _get_theme_editor_dir()
_BOOTSTRAP4_SCSS = os.path.join(
    _THEME_EDITOR_DIR, 'node_modules', 'bootstrap', 'scss', 'bootstrap.scss'
)

def _sanitize_scss_value(variable_name, value):
    """Return value if it is safe to embed in a SCSS declaration; log and return None otherwise.

    Rejects values containing SCSS directives or syntax that could break out of a
    variable declaration and inject arbitrary SCSS.  This is an admin-only surface
    but defence-in-depth is warranted since compiled CSS is served to all users.
    """
    if re.search(r'@import\b|url\s*\(|[;{}]', value, re.IGNORECASE):
        logger.warning(
            'Rejected suspicious SCSS variable value for %r: %r', variable_name, value
        )
        return None
    return value

# MD5 of bundled placeholder logo (black square + "Placeholder logo" text)
PLACEHOLDER_LOGO_MD5 = '26ef721aabd025a813006aea9af71802'
THEME_COMPILED_WARNING = textwrap.dedent("""\
    /**********************************************************************
    ***                     DO NOT EDIT THIS FILE!                      ***
    ***    This file is automatically generated from theme settings.    ***
    ***      Any changes will be *deleted* the next time there are      ***
    ***        updates to the theme.  Go to the theme editor at         ***
    ***    yoursite.learningu.org/themes to edit theme settings, or     ***
    ***     contact websupport@learningu.org if you have questions.     ***
    **********************************************************************/

    """)

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
            if name != '__pycache__' and os.path.isdir(os.path.join(THEME_PATH, name))]

    def get_bootswatch_themes(self):
        """Return sorted list of Bootswatch 3 theme names available from npm.

        Returns an empty list when the npm package is not installed.
        """
        bootswatch_dir = os.path.normpath(os.path.join(
            themes_settings.less_dir, '..', 'node_modules', 'bootswatch'
        ))
        if not os.path.isdir(bootswatch_dir):
            return []
        return sorted(
            name for name in os.listdir(bootswatch_dir)
            if os.path.isdir(os.path.join(bootswatch_dir, name))
            and os.path.exists(os.path.join(bootswatch_dir, name, 'variables.less'))
        )

    def get_template_settings(self):
        """
        Get the current template settings. The base settings are the initial
        values of the configuration form fields, which are overridden by values
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
        # Restrict to known-safe theme directory names before touching the filesystem.
        if not re.fullmatch(r'[A-Za-z0-9_-]+', theme_name):
            raise ValueError(f'Invalid theme name: {theme_name!r}')
        # Resolve and verify the path stays inside THEME_PATH to prevent traversal.
        resolved = os.path.realpath(os.path.join(THEME_PATH, theme_name))
        theme_root = os.path.realpath(THEME_PATH)
        if not resolved.startswith(theme_root + os.sep) and resolved != theme_root:
            raise ValueError(f'Invalid theme name: {theme_name!r}')
        return resolved

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
                        full_name = (f'{dirpath[bd_len:]}/{filename}')[1:]
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
            theme_form_module = __import__(f'esp.themes.theme_data.{theme_name}.config_form', (), (), 'ConfigForm')
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

    def get_less_names(self, theme_name, theme_only=False, bootswatch_theme=None):
        result = []
        if not theme_only:
            result += self.global_less()

            if bootswatch_theme:
                valid_bootswatch = self.get_bootswatch_themes()
                if bootswatch_theme not in valid_bootswatch:
                    raise ValueError(f'Unknown Bootswatch theme: {bootswatch_theme!r}')
                # Bootswatch variables must precede bootstrap.less to override its defaults.
                # Wrong order = Bootswatch colors have zero effect.
                result.append(os.path.normpath(os.path.join(
                    themes_settings.less_dir, '..', 'node_modules', 'bootswatch',
                    bootswatch_theme, 'variables.less'
                )))

            # Bootstrap 3.3.7 is installed via npm; run 'npm install' in
            # esp/public/media/theme_editor/ before compiling.
            # Bootstrap 3 has responsive styles built into bootstrap.less —
            # no separate responsive.less is needed.
            result.append(os.path.normpath(os.path.join(
                themes_settings.less_dir, '..', 'node_modules', 'bootstrap', 'less', 'bootstrap.less'
            )))

            if bootswatch_theme:
                # Bootswatch component styles must follow bootstrap.less
                result.append(os.path.normpath(os.path.join(
                    themes_settings.less_dir, '..', 'node_modules', 'bootswatch',
                    bootswatch_theme, 'bootswatch.less'
                )))

            result.append(os.path.join(themes_settings.less_dir, 'variables_custom.less'))
            result.append(os.path.join(themes_settings.less_dir, 'main.less'))

        #   Make sure variables.less is included first, before any other custom LESS code
        theme_files = self.list_filenames(os.path.join(self.base_dir(theme_name), 'less'), r'\.less$')
        nonvariable_files = []
        for theme_file in theme_files:
            if os.path.basename(theme_file).startswith('variables'):
                result.append(theme_file)
            else:
                nonvariable_files.append(theme_file)
        result += nonvariable_files

        return result

    def find_theme_variables(self, theme_name=None, theme_only=False, flat=False):
        """Return theme variable definitions using the SCSS or LESS pipeline."""
        if theme_name is None:
            theme_name = self.get_current_theme()
        if self.uses_scss_pipeline(theme_name):
            return self.find_scss_variables(theme_name, theme_only=theme_only, flat=flat)
        return self.find_less_variables(theme_name, theme_only=theme_only, flat=flat)

    def find_less_variables(self, theme_name=None, theme_only=False, flat=False):
        if theme_name is None:
            theme_name = self.get_current_theme()

        #   Return value is a mapping of names to default values (both strings)
        results = {}
        for filename in self.get_less_names(theme_name, theme_only=theme_only):
            if not os.path.isfile(filename):
                logger.debug('find_less_variables: skipping missing file %s', filename)
                continue
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

    def compile_less(self, less_data):
        #   Hack to make things work on Windows systems
        INCLUDE_PATH_SEP = ':'
        if os.name == 'nt':
            INCLUDE_PATH_SEP = ';'

        # Include Bootstrap 3 LESS from npm so @imports inside bootstrap.less resolve
        bootstrap3_less_dir = os.path.join(settings.MEDIA_ROOT, 'theme_editor', 'node_modules', 'bootstrap', 'less')
        less_search_path = INCLUDE_PATH_SEP.join(
            settings.LESS_SEARCH_PATH +
            [os.path.join(settings.MEDIA_ROOT, 'theme_editor', 'less'), bootstrap3_less_dir]
        )
        logger.debug('LESS search path is "%s"', less_search_path)

        #   Compile to CSS
        lessc_args = ['lessc', '--include-path=%s' % less_search_path, '-']
        lessc_process = subprocess.Popen(lessc_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        css_data = lessc_process.communicate(less_data.encode())[0]

        if lessc_process.returncode != 0:
            logger.error('lessc failed (code %d). Compiler output:\n%s',
                         lessc_process.returncode,
                         css_data.decode('UTF-8', 'replace'))
            raise ESPError(f'The stylesheet compiler (lessc) returned error code {lessc_process.returncode}.  Please check the LESS sources and settings you are using to generate the theme, or if you are using a provided theme please contact the <a href="mailto:{settings.DEFAULT_EMAIL_ADDRESSES["support"]}">Web support team</a>.<br />LESS compile command was: <pre>{" ".join(lessc_args)}</pre>', log=True)

        return css_data

    def has_scss(self, theme_name):
        """Return True if this theme uses the SCSS/Bootstrap 4 pipeline.

        Delegates to the module-level _SCSS_THEMES frozenset which was
        computed at import time without user input, so no path expression
        involving theme_name is needed here.
        """
        return theme_name in _SCSS_THEMES

    def _bootstrap3_less_available(self):
        """Return True when the legacy Bootstrap 3 LESS npm package is installed."""
        bootstrap3_less = os.path.join(
            settings.MEDIA_ROOT, 'theme_editor', 'node_modules', 'bootstrap', 'less', 'bootstrap.less'
        )
        return os.path.isfile(bootstrap3_less)

    def uses_scss_pipeline(self, theme_name):
        """Return True when compile/get_variable_defaults should use SCSS/Bootstrap 4."""
        return self.has_scss(theme_name) or not self._bootstrap3_less_available()

    def get_scss_names(self, theme_name, theme_only=False):
        """Return ordered list of SCSS files to concatenate for compilation."""
        result = []
        if not theme_only:
            # Theme-editor-level variables must come BEFORE Bootstrap so that
            # Bootstrap's !default variables pick up our overrides.
            result.append(os.path.join(themes_settings.scss_dir, 'variables_custom.scss'))
            result.append(os.path.join(themes_settings.scss_dir, 'main.scss'))

        # Theme-specific SCSS files.  Look up the pre-computed directory from
        # _SCSS_THEME_DIRS (an import-time constant) so theme_name never appears
        # in an os.path.join expression — CodeQL sees the path as untainted.
        theme_scss_dir = _SCSS_THEME_DIRS.get(theme_name)
        if theme_scss_dir is None:
            theme_files = []
        else:
            theme_files = self.list_filenames(theme_scss_dir, r'\.scss$')
        variable_files = []
        nonvariable_files = []
        for theme_file in theme_files:
            if os.path.basename(theme_file).startswith('variables'):
                variable_files.append(theme_file)
            else:
                nonvariable_files.append(theme_file)
        variable_files.sort(
            key=lambda f: (0 if os.path.basename(f) == 'variables.scss' else 1, f)
        )
        result += variable_files
        result += nonvariable_files
        return result

    def find_scss_variables(self, theme_name=None, theme_only=False, flat=False):
        if theme_name is None:
            theme_name = self.get_current_theme()
        # Validate each path against known safe roots before any file operation.
        # os.path.realpath + startswith is the CodeQL-recommended sanitisation pattern
        # for py/path-injection (see CodeQL docs: "Uncontrolled data in path expression").
        _safe_roots = (
            os.path.realpath(THEME_PATH) + os.sep,
            os.path.realpath(themes_settings.scss_dir) + os.sep,
        )
        results = {}
        for filename in self.get_scss_names(theme_name, theme_only=theme_only):
            safe_filename = os.path.realpath(filename)
            if not any(safe_filename.startswith(root) for root in _safe_roots):
                logger.warning('find_scss_variables: rejecting path outside safe roots: %s', filename)
                continue
            if not os.path.isfile(safe_filename):
                logger.debug('find_scss_variables: skipping missing file %s', safe_filename)
                continue
            local_results = {}
            logger.debug('find_scss_variables: including file %s', safe_filename)
            with open(safe_filename) as f:
                scss_data = f.read()
            for item in re.findall(r'\$([a-zA-Z0-9_]+):\s*(.*?);', scss_data):
                local_results[item[0]] = item[1]
            if flat:
                results.update(local_results)
            else:
                results[safe_filename] = local_results
        return results

    def compile_scss(self, scss_data):
        """Compile SCSS source string using dart-sass, return CSS bytes."""
        theme_editor_dir = _THEME_EDITOR_DIR
        node_modules_dir = 'node_modules'
        scss_dir = 'scss'
        sass_js = os.path.join(node_modules_dir, 'sass', 'sass.js')
        sass_args = [
            'node',
            sass_js,
            '--stdin',
            f'--load-path={node_modules_dir}',
            f'--load-path={scss_dir}',
            '--no-source-map',
        ]
        sass_process = subprocess.Popen(
            sass_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=theme_editor_dir,
        )
        css_data, _ = sass_process.communicate(scss_data.encode())

        if sass_process.returncode != 0:
            sass_output = css_data.decode('UTF-8', errors='replace')
            raise ESPError(
                f'The stylesheet compiler (sass) returned error code {sass_process.returncode}. '
                f'Please check the SCSS sources and settings you are using to generate the theme, '
                f'or contact the <a href="mailto:{settings.DEFAULT_EMAIL_ADDRESSES["support"]}">Web support team</a>.'
                f'<br />SCSS compile command was: <pre>{" ".join(sass_args)}</pre>'
                f'<br />Sass output: <pre>{sass_output}</pre>',
                log=True,
            )
        return css_data

    def get_variable_defaults(self, theme_name=None):
        # This is particularly important for themes that have variables files with LESS (e.g., darken())
        # Otherwise it basically does the same thing as find_less_variables()
        if theme_name is None:
            theme_name = self.get_current_theme()
        # Constrain theme_name to the import-time frozenset of known theme names.
        # _ALL_THEMES is not derived from user input, so membership here breaks
        # the taint chain before any path expression below.
        if theme_name not in _ALL_THEMES:
            theme_name = 'barebones'

        if theme_name in _SCSS_THEMES:
            # For SCSS themes the declared variable values are the defaults.
            # Use find_scss_variables() which reads via the _SCSS_THEMES-gated
            # get_scss_names() — no user-derived content reaches a subprocess.
            return self.find_scss_variables(theme_name, flat=True)

        # LESS pipeline — theme_name is now constrained to _ALL_THEMES.
        # Import global bootstrap variable definitions and custom overrides first so
        # theme variables that reference them (e.g. @navbarInverseBackground) resolve
        # correctly during the isolated compilation below.
        less_data = ''
        # load variable LESS from files
        for filename in self.list_filenames(os.path.join(THEME_PATH, theme_name, 'less'), r'variables.*\.less$'):
            less_file = open(filename)
            logger.debug('Including LESS source %s', filename)
            less_data += '\n' + less_file.read()
            less_file.close()

        # add list of variables
        # this is a hack to convert the less variables to pseudo-css compiled variables
        # which we can then extract as a python dictionary
        less_data += '\ndiv {'
        for item in re.findall(r'@([a-zA-Z0-9_]+):\s*(.*?);', less_data):
            less_data += '\n' + item[0]
            less_data += ': @' + item[0] + ';'
        less_data += '\n}'

        # compile to CSS
        css_data = self.compile_less(less_data)

        # extract the newly compiled variables
        compiled_defaults = dict(re.findall(r'\s([a-zA-Z0-9_]+):\s*(.*?);', css_data.decode('UTF-8')))
        defaults = self.find_less_variables(theme_name, flat=True)
        defaults.update(compiled_defaults)

        return defaults

    def compile_css(self, theme_name, variable_data, output_filename, bootswatch_theme=None):
        if theme_name in _SCSS_THEMES:
            # SCSS/Bootstrap 4 pipeline.  theme_name is constrained to the
            # import-time _SCSS_THEMES frozenset, breaking the taint chain
            # before any path expression or subprocess call below.
            scss_data = ''
            for filename in self.get_scss_names(theme_name):
                with open(filename) as f:
                    logger.debug('Including SCSS source %s', filename)
                    scss_data += '\n' + f.read()

            # Bootstrap 4 is imported inline (not concatenated) so dart-sass
            # can resolve its own @imports via --load-path.
            # _BOOTSTRAP4_SCSS is a module-level constant validated against MEDIA_ROOT at import time.
            bootstrap_import = f'\n@import "{_BOOTSTRAP4_SCSS}";\n'
            scss_data = scss_data + bootstrap_import

            #   Replace all SCSS variable declarations for which we have a value defined.
            #   Parse variable names from the already-loaded scss_data (server content,
            #   not user input) so the name used in re.sub is never tainted by user data.
            known_var_names = set(re.findall(r'\$([a-zA-Z0-9_-]+):', scss_data))
            for variable_name in known_var_names:
                if variable_name not in variable_data:
                    continue
                safe_value = _sanitize_scss_value(variable_name, variable_data[variable_name])
                if safe_value is None:
                    continue
                scss_data = re.sub(
                    rf'\${re.escape(variable_name)}:(\s*)(.*?);',
                    f'${variable_name}: {safe_value};',
                    scss_data,
                )

            css_data = self.compile_scss(scss_data)
        else:
            #   Load LESS files in order of search path
            less_data = ''
            for filename in self.get_less_names(theme_name, bootswatch_theme=bootswatch_theme):
                less_file = open(filename)
                logger.debug('Including LESS source %s', filename)
                less_data += '\n' + less_file.read()
                less_file.close()

            #   Make icon image path load from the CDN by default
            if 'iconSpritePath' not in variable_data:
                variable_data['iconSpritePath'] = f'"{settings.CDN_ADDRESS}/bootstrap/img/glyphicons-halflings.png"'

            #   Replace all variable declarations for which we have a value defined
            for (variable_name, variable_value) in variable_data.items():
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', variable_name):
                    continue
                less_data = re.sub(
                    rf'@{re.escape(variable_name)}:(\s*)(.*?);',
                    lambda match, vn=variable_name, vv=variable_value: f'@{vn}: {vv};',
                    less_data,
                )

            css_data = self.compile_less(less_data)

        with open(output_filename, 'w') as output_file:
            output_file.write(str(THEME_COMPILED_WARNING) + css_data.decode('UTF-8'))
        logger.debug('Wrote %.1f KB CSS output to %s', len(css_data) / 1000., output_filename)
        Tag.setTag("current_theme_version", value = hex(random.getrandbits(16)))

    def recompile_theme(self, theme_name=None, customization_name=None, keep_files=None):
        """
        Reloads the theme (possibly updating the template overrides with recent
        code changes), then recompiles the customizations.
        """
        if settings.LOCAL_THEME:
            return
        if (customization_name is None) or (customization_name == "None"):
            customization_name = self.get_current_customization()
        if theme_name is None:
            theme_name = self.get_current_theme()

        # Save current parameters and palette before they are cleared
        current_vars = self.get_current_params()
        current_palette = json.loads(Tag.getTag('current_theme_palette', default='[]'))

        backup_info = self.clear_theme(keep_files=keep_files)
        self.load_theme(theme_name, backup_info=backup_info)
        self.update_template_settings()

        vars = current_vars
        palette = current_palette

        if customization_name is not None and customization_name != "None":
            try:
                (vars, palette) = self.load_customizations(customization_name)
            except FileNotFoundError:
                logger.warning("Customization file for %s missing. Initializing with parameters from database.", customization_name)
                self.save_customizations(customization_name, theme_name=theme_name, vars=current_vars, palette=current_palette)
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

        #   If files are to be preserved, copy them to temporary locations
        #   and return a record of those locations (backup_info).
        #   This is much easier than writing new functions for removing and
        #   copying directory trees.
        backup_info = self.backup_files(settings.MEDIA_ROOT, keep_files)
        images_theme_dir = os.path.join(settings.MEDIA_ROOT, 'images', 'theme')
        scripts_theme_dir = os.path.join(settings.MEDIA_ROOT, 'scripts', 'theme')
        if os.path.exists(images_theme_dir):
            shutil.rmtree(images_theme_dir, ignore_errors=True)
        if os.path.exists(scripts_theme_dir):
            shutil.rmtree(scripts_theme_dir, ignore_errors=True)

        #   Remove compiled CSS file
        if os.path.exists(self.css_filename):
            os.remove(self.css_filename)

        Tag.unSetTag('current_theme_name')
        Tag.unSetTag('current_theme_params')
        Tag.unSetTag('current_theme_palette')
        Tag.unSetTag('current_theme_version')
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
            if filename == '__pycache__':
                continue
            full_filename = os.path.join(dir, filename)
            if os.path.isdir(full_filename):
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
                        'filename_hash': hashlib.sha1(rel_filename_dest.encode("UTF-8")).hexdigest(),
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

    def ensure_theme_media(self):
        """Restore logo/header from defaults when missing or still the placeholder."""
        theme_dir = os.path.join(settings.MEDIA_ROOT, 'images', 'theme')
        default_dir = os.path.join(settings.MEDIA_ROOT, 'default_images', 'theme')
        os.makedirs(theme_dir, exist_ok=True)

        for filename, tag_name in (
            ('logo.png', 'current_logo_version'),
            ('header.png', 'current_header_version'),
        ):
            dest = os.path.join(theme_dir, filename)
            src = os.path.join(default_dir, filename)
            replace = not os.path.exists(dest)
            if os.path.exists(dest) and filename == 'logo.png':
                with open(dest, 'rb') as logo_file:
                    replace = hashlib.md5(logo_file.read()).hexdigest() == PLACEHOLDER_LOGO_MD5
            if replace and os.path.exists(src):
                shutil.copy2(src, dest)
            if os.path.exists(dest):
                Tag.setTag(tag_name, value=hex(int(os.path.getmtime(dest))))

    def load_theme(self, theme_name, **kwargs):

        #   Create template overrides using data provided (our models handle versioning)
        logger.debug('Loading theme: %s', theme_name)

        #   Collect LESS files from appropriate sources and compile CSS
        self.compile_css(theme_name, {}, self.css_filename)

        theme_base_dir = self.base_dir(theme_name)

        #   Copy images and script files to the active theme directory
        img_src_dir = os.path.join(theme_base_dir, 'images')
        if os.path.exists(img_src_dir):
            img_dest_dir = os.path.join(settings.MEDIA_ROOT, 'images', 'theme')
            shutil.copytree(img_src_dir, img_dest_dir, dirs_exist_ok=True)
        script_src_dir = os.path.join(theme_base_dir, 'scripts')
        if os.path.exists(script_src_dir):
            script_dest_dir = os.path.join(settings.MEDIA_ROOT, 'scripts', 'theme')
            shutil.copytree(script_src_dir, script_dest_dir, dirs_exist_ok=True)

        #   If files need to be restored, copy them back to the desired locations.
        if kwargs.get('backup_info', None) is not None:
            self.restore_files(settings.MEDIA_ROOT, kwargs['backup_info'])

        self.ensure_theme_media()

        Tag.setTag('current_theme_name', value=theme_name)
        Tag.setTag('current_theme_params', value='{}')
        Tag.unSetTag('current_theme_palette')
        self.unset_current_customization()

        #   Clear the Varnish cache
        varnish.purge_all()

    def customize_theme(self, vars):
        logger.debug('Customizing theme with variables: %s', vars)
        self.compile_css(self.get_current_theme(), vars, self.css_filename)
        vars_available = self.find_theme_variables(self.get_current_theme(), flat=True)
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

    def _safe_customization_path(self, save_name):
        """Return a validated absolute path for a customization file.

        Raises SuspiciousFileOperation if the resolved path escapes themes_dir.
        """
        safe_dir = os.path.realpath(themes_settings.themes_dir)
        # Validate the raw name BEFORE quoting — quote() would encode '/' and
        # '..' into harmless percent-encoded literals, hiding real traversal.
        raw_path = os.path.realpath(os.path.join(themes_settings.themes_dir, f'{save_name}.less'))
        if not raw_path.startswith(f'{safe_dir}{os.sep}'):
            raise SuspiciousFileOperation(f'Attempted path traversal in theme save name: {save_name!r}')
        # Build the final path with URL-quoted name and validate it too so
        # that CodeQL's taint analysis sees the returned value as sanitized.
        path = os.path.realpath(os.path.join(safe_dir, f'{quote(save_name, safe="")}.less'))
        if not path.startswith(f'{safe_dir}{os.sep}'):
            raise SuspiciousFileOperation(f'Attempted path traversal in theme save name: {save_name!r}')
        return path

    def save_customizations(self, save_name, theme_name=None, vars=None, palette=None):
        if theme_name is None:
            theme_name = self.get_current_theme()
        if vars is None:
            vars = self.get_current_params()
        if palette is None:
            palette = self.get_palette()['custom']

        vars_orig = self.find_theme_variables(theme_name, flat=True)
        keys = copy.copy(list(vars.keys()))
        for key in keys:
            if key not in vars_orig:
                del vars[key]

        context = {}
        context['vars'] = vars
        context['base_theme'] = theme_name
        context['save_name'] = save_name
        context['palette'] = palette

        with open(self._safe_customization_path(save_name), 'w') as f:
            f.write(render_to_string('themes/custom_vars.less', context))

    def load_customizations(self, save_name):

        with open(self._safe_customization_path(save_name), 'r') as f:
            data = f.read()

        #   Collect LESS variables
        vars = {}
        for match in re.findall(r'@(\w+):\s*(.*?);', data):
            vars[match[0]] = match[1]

        #   Substitute LESS variables
        for key, val in vars.items():
            if val[1:len(val)] in list(vars.keys()):
                vars[key] = vars[val[1:len(val)]]

        #   Collect save name stored in file
        save_name_match = re.search(r'// Theme Name: (.+?)\n', data)
        if save_name_match:
            assert(save_name == save_name_match.group(1))

        #   Collect palette
        palette = set()
        for match in re.findall(r'palette:(#?\w+?);', data):
            if len(match) == 4: # Convert to long form
                match = '#' + match[1] + match[1] + match[2] + match[2] + match[3] + match[3]
            palette.add(match)
        palette = list(palette)

        self.set_current_customization(save_name)

        logger.debug("vars: %s", vars)
        logger.debug("palette: %s", palette)
        return (vars, palette)

    def delete_customizations(self, save_name):
        os.remove(self._safe_customization_path(save_name))

    def get_customization_names(self):
        result = []
        filenames = os.listdir(os.path.join(themes_settings.themes_dir))
        for fn in filenames:
            if fn.endswith('.less'):
                result.append(unquote(fn[:-5]))
        return result

    ##  Palette getter/setter -- palette is a list of strings which each contain
    ##  HTML color codes, e.g. ["#FFFFFF", "#3366CC"]

    ## Returns a dictionary with the theme's base palette and the custom tag-defined palette
    def get_palette(self):
        palette_custom = json.loads(Tag.getTag('current_theme_palette', default='[]'))

        #   Collect colors from any global LESS variables
        palette_base = set()
        base_vars = self.find_theme_variables(theme_only=False, flat=False)
        for varset in base_vars.values():
            for val in varset.values():
                if isinstance(val, str) and val.startswith('#'):
                    if len(val) == 4: # Convert to long form
                        val = '#' + val[1] + val[1] + val[2] + val[2] + val[3] + val[3]
                    palette_base.add(val)

        palette_base = sorted(palette_base)

        return {'base': palette_base, 'custom': palette_custom}

    def set_palette(self, palette):
        #   Remove global theme variables from the palette
        palette = set(palette)
        base_vars = self.find_theme_variables(theme_only=False, flat=False)
        for varset in base_vars.values():
            for val in varset.values():
                if isinstance(val, str) and val.startswith('#'):
                    if len(val) == 4: # Convert to long form
                        val = '#' + val[1] + val[1] + val[2] + val[2] + val[3] + val[3]
                    if val in palette:
                        palette.remove(val)

        palette = sorted(palette)
        Tag.setTag('current_theme_palette', value=json.dumps(palette))
