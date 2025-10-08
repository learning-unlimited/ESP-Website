from __future__ import absolute_import
from django.conf import settings

from os import path
from collections import OrderedDict

# can we avoid hardcoding this?
less_dir = path.join(settings.PROJECT_ROOT, 'public', 'media', 'theme_editor', 'less') #directory containing less files used by theme editor
themes_dir = path.join(settings.PROJECT_ROOT, 'public', 'media', 'theme_editor', 'themes') #directory containing the themes
variables_less = path.join(less_dir, 'variables.less')
# directory containing the javascript that shows the palette
palette_dir = path.join(settings.PROJECT_ROOT, 'public', 'media', 'theme_editor')

# and this...
sans_serif_fonts = OrderedDict([("Arial", "Arial, sans-serif"),
                    ("Arial Black", "'Arial Black', sans-serif"),
                    ("Arial Narrow", "'Arial Narrow', sans-serif"),
                    ("Century Gothic", "'Century Gothic', sans-serif"),
                    ("Gill Sans", "'Gill Sans', sans-serif"),
                    ("Helvetica",  "Helvetica, sans-serif"),
                    ("Impact", "Impact, Charcoal, sans-serif"),
                    ("Lucida Sans Unicode", "'Lucida Sans Unicode', sans-serif"),
                    ("Optima", "Optima, sans-serif"),
                    ("Tahoma", "Tahoma, Geneva, sans-serif"),
                    ("Trebuchet MS", "'Trebuchet MS', sans-serif"),
                    ("Verdana", "Verdana, Geneva, sans-serif"),
                    ("American Typewriter", "'American Typewriter', serif"),
                    ("Bookman", "Bookman, serif"),
                    ("Copperplate Gothic Light", "'Copperplate Gothic Light', serif"),
                    ("Didot", "Didot, serif"),
                    ("Georgia", "Georgia, serif"),
                    ("Palatino Linotype", "'Palatino Linotype', serif"),
                    ("Times", "Times, serif"),
                    ("Times New Roman", "'Times New Roman', serif"),
                    ("Andale Mono", "'Andale Mono', monospace"),
                    ("Courier New", "'Courier New', monospace"),
                    ("Lucida Console", "'Lucida Console', monospace"),
                    ("Monaco", "Monaco, monospace"),
                    ("Apple Chancery", "'Apple Chancery', cursive"),
                    ("Bradley Hand", "'Bradley Hand', cursive"),
                    ("Brush Script MT", "'Brush Script MT', cursive"),
                    ("Comic Sans MS", "'Comic Sans MS', cursive"),
                    ])

THEME_DEBUG = False
COMPILED_CSS_FILE = "theme_compiled.css"

