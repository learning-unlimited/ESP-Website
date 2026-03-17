"""Tests for the esp.dbmail.views module.

The views module currently contains only a license header and
the default Django placeholder comment (``# Create your views here.``).
These tests verify the module loads correctly and document its
empty public API so that any future additions are covered.
"""

import importlib
import importlib.util
import inspect
import os
import types

# Absolute path to the views.py file, resolved relative to this test file.
_VIEWS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "views.py",
)


def _load_views_module():
    """Load esp/dbmail/views.py directly from the filesystem.

    This avoids requiring a fully configured Django environment,
    which is appropriate because views.py currently has no Django
    imports.  When Django *is* available (e.g. in CI), the standard
    ``importlib.import_module`` path is used instead so the module
    is exercised through the real package hierarchy.
    """
    try:
        return importlib.import_module("esp.dbmail.views")
    except Exception:
        spec = importlib.util.spec_from_file_location(
            "esp.dbmail.views", _VIEWS_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class TestViewsModuleImport:
    """Verify that the esp.dbmail.views module can be imported correctly."""

    def test_import_module(self):
        """The views module should import without raising any errors."""
        module = _load_views_module()
        assert isinstance(module, types.ModuleType)

    def test_module_name(self):
        """The imported module should have the expected qualified name."""
        module = _load_views_module()
        assert module.__name__ == "esp.dbmail.views"

    def test_views_file_exists(self):
        """The views.py file should exist on disk."""
        assert os.path.isfile(_VIEWS_PATH)


class TestViewsModuleContents:
    """Verify that the views module's public surface is as expected."""

    def test_no_view_functions_defined(self):
        """The module currently defines no view functions.

        This test documents the current state (0% coverage baseline).
        If view functions are added later, this test should be updated
        to reflect the new public API.
        """
        module = _load_views_module()
        # Collect only functions defined *in* this module (not imports)
        locally_defined = [
            name
            for name, obj in inspect.getmembers(module, inspect.isfunction)
            if obj.__module__ == module.__name__
        ]
        assert locally_defined == []

    def test_no_class_based_views_defined(self):
        """The module should not define any class-based views."""
        module = _load_views_module()
        locally_defined_classes = [
            name
            for name, obj in inspect.getmembers(module, inspect.isclass)
            if obj.__module__ == module.__name__
        ]
        assert locally_defined_classes == []

    def test_module_has_no_url_patterns(self):
        """The module should not expose a urlpatterns list."""
        module = _load_views_module()
        assert not hasattr(module, "urlpatterns")

    def test_module_metadata(self):
        """The module should carry the standard ESP license metadata."""
        module = _load_views_module()
        assert hasattr(module, "__license__")
        assert module.__license__ == "AGPL v.3"
