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
    # Replace forms.forms.BoundField with forms.boundfield.BoundField
    find "$FORM_UTILS_PATH" -name "*.py" -exec sed -i 's/forms\.forms\.BoundField/forms.boundfield.BoundField/g' {} \;
    
    # Also need to add the import for boundfield module where forms is imported
    # In forms.py, after "from django import forms", add "from django.forms import boundfield"
    if [ -f "$FORM_UTILS_PATH/forms.py" ]; then
        # Check if the import already exists to avoid duplicates
        if ! grep -q "from django.forms import boundfield" "$FORM_UTILS_PATH/forms.py"; then
            sed -i '/from django import forms/a from django.forms import boundfield' "$FORM_UTILS_PATH/forms.py"
        fi
    fi
    
    echo "  ✓ django-form-utils patched"
fi

echo "All packages patched successfully"

