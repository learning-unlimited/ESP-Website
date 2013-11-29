from django.conf import settings

from os import path

# can we avoid hardcoding this?
less_dir = path.join(settings.PROJECT_ROOT, 'public','media','theme_editor','less') #directory containing less files used by theme editor
themes_dir = path.join(settings.PROJECT_ROOT, 'public','media','theme_editor','themes') #directory containing the themes
variables_less = path.join(less_dir, 'variables.less')
# directory containing the javascript that shows the palette
palette_dir = path.join(settings.PROJECT_ROOT, 'public','media','theme_editor')

# and this...
sans_serif_fonts = {"Impact":"Impact, Charcoal, sans-serif",
                    "Palatino Linotype":"'Palatino Linotype', 'Book Antiqua', Palatino, serif",
                    "Tahoma":"Tahoma, Geneva, sans-serif",
                    "Century Gothic":"'Century Gothic', sans-serif",
                    "Lucida Sans Unicode":"'Lucida Sans Unicode', 'Lucida Grande', sans-serif",
                    "Arial Black":"'Arial Black', Gadget, sans-serif",
                    "Times New Roman":"'Times New Roman', Times, serif",
                    "Arial Narrow":"'Arial Narrow', sans-serif",
                    "Verdana":"Verdana, Geneva, sans-serif",
                    "Copperplate Gothic Light":"'Copperplate Gothic Light', Copperplate, sans-serif",
                    "Lucida Console":"'Lucida Console', Monaco, monospace",
                    "Gill Sans":"'Gill Sans', 'Gill Sans MT', sans-serif",
                    "Trebuchet MS":"'Trebuchet MS', Helvetica', sans-serif",
                    "Courier New":"'Courier New', Courier, monospace",
                    "Arial":"Arial, Helvetica, sans-serif",
                    "Georgia":"Georgia, serif"}

THEME_DEBUG = False
COMPILED_CSS_FILE = "theme_compiled.css"

