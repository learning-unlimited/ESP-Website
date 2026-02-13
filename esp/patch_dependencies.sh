#!/bin/bash
# Patch third-party packages to be compatible with Django 3.x
# This is needed because some packages are unmaintained and use removed Django APIs

set -e

echo "Patching third-party packages for Django 3.x compatibility..."

# Patch django-form-utils
FORM_UTILS_PATH=$(python3 -c "import form_utils; import os; print(os.path.dirname(form_utils.__file__))" 2>/dev/null || echo "")
if [ -n "$FORM_UTILS_PATH" ]; then
    echo "Patching django-form-utils at: $FORM_UTILS_PATH"
    find "$FORM_UTILS_PATH" -name "*.py" -exec sed -i 's/from django\.utils import six/import six/g' {} \;
    find "$FORM_UTILS_PATH" -name "*.py" -exec sed -i '/from django\.utils\.encoding import python_2_unicode_compatible/d' {} \;
    find "$FORM_UTILS_PATH" -name "*.py" -exec sed -i '/@python_2_unicode_compatible/d' {} \;
    
    # Fix BoundField import - in Django 3.1+, BoundField is in django.forms.boundfield
    find "$FORM_UTILS_PATH" -name "*.py" -exec sed -i 's/forms\.forms\.BoundField/forms.boundfield.BoundField/g' {} \;
    
    echo "  ✓ django-form-utils patched"
fi

# Patch django-argcache (find it without importing)
ARGCACHE_PATH=$(python3 -c "import sys; paths = [p for p in sys.path if 'site-packages' in p]; import os; argcache = next((os.path.join(p, 'argcache') for p in paths if os.path.exists(os.path.join(p, 'argcache'))), None); print(argcache if argcache else '')" 2>/dev/null || echo "")
if [ -n "$ARGCACHE_PATH" ]; then
    echo "Patching django-argcache at: $ARGCACHE_PATH"
    
    # Fix getargspec -> getfullargspec
    if [ -f "$ARGCACHE_PATH/function.py" ]; then
        sed -i 's/params, varargs, keywords, _ = inspect\.getargspec(func)/argspec = inspect.getfullargspec(func)\n        params, varargs, keywords = argspec.args, argspec.varargs, argspec.varkw/' "$ARGCACHE_PATH/function.py"
    fi
    
    # Fix django.utils.six imports
    find "$ARGCACHE_PATH" -name "*.py" -exec sed -i 's/from django\.utils import six/import six/g' {} \;
    
    # Fix render_to_response
    if [ -f "$ARGCACHE_PATH/views.py" ]; then
        sed -i 's/from django.shortcuts import redirect, render_to_response/from django.shortcuts import redirect, render/g' "$ARGCACHE_PATH/views.py"
        sed -i 's/render_to_response(/render(request, /g' "$ARGCACHE_PATH/views.py"
    fi
    
    echo "  ✓ django-argcache patched"
fi

echo "All packages patched successfully"

