"""Tests for admin dashboard search (get_admin_search_entries, serialization, safety)."""
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.admin_search import (
    EXCLUDED_VIEW_NAMES,
    get_admin_search_entries,
    serialize_admin_search_entries,
    _humanize_view_name,
    AdminSearchEntry,
)


class AdminSearchEntriesTest(ProgramFrameworkTest):
    """Test that admin search entries are built correctly and exclude invalid links."""

    def setUp(self):
        super().setUp(modules=[ProgramModule.objects.get(handler='AdminCore')])

    def test_returns_list_of_entries(self):
        entries = get_admin_search_entries(self.program)
        self.assertIsInstance(entries, list)
        self.assertGreater(len(entries), 0, "Program with AdminCore should have at least one search entry")
        for e in entries:
            self.assertIsInstance(e, AdminSearchEntry)
            self.assertTrue(e.id, "entry should have id")
            self.assertTrue(e.url, "entry should have url")
            self.assertTrue(len(e.title) >= 0, "entry should have title")
            self.assertTrue(e.category, "entry should have category")
            self.assertIsInstance(e.keywords, list, "entry should have keywords list")

    def test_keywords_contain_tl_and_view_name(self):
        """Keywords should include the module area (tl) and technical view name for discovery."""
        entries = get_admin_search_entries(self.program)
        for e in entries:
            # e.id is formed as tl_viewname
            tl, view_name = e.id.split('_', 1)
            self.assertIn(tl, e.keywords, "Keywords for %s should include area %r" % (e.id, tl))
            self.assertIn(view_name, e.keywords, "Keywords for %s should include view name %r" % (e.id, view_name))

    def test_entries_have_required_fields(self):
        """Every listed entry has non-empty title, keywords, url, and id."""
        entries = get_admin_search_entries(self.program)
        for e in entries:
            self.assertTrue(e.title, "Every entry should have a non-empty title")
            self.assertTrue(e.keywords, "Every entry should have at least one keyword")
            self.assertTrue(e.url.startswith('/'), "URL should be absolute path")
            self.assertTrue(e.id, "Every entry should have an id")

    def test_excluded_views_not_in_results(self):
        """Class-specific views (editclass, manageclass, etc.) must not appear in search."""
        entries = get_admin_search_entries(self.program)
        entry_ids = {e.id for e in entries}
        for excluded in EXCLUDED_VIEW_NAMES:
            found = [e for e in entries if excluded in e.id.lower() or excluded in e.url.lower()]
            self.assertEqual(found, [], "Excluded view %r should not appear in search results" % excluded)

    def test_serialize_returns_list_of_dicts(self):
        data = serialize_admin_search_entries(self.program)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        for d in data:
            self.assertIsInstance(d, dict)
            for key in ('id', 'url', 'title', 'category', 'keywords'):
                self.assertIn(key, d, "Serialized entry should have key %r" % key)
            self.assertIsInstance(d['keywords'], list)

    def test_humanize_view_name(self):
        """View names are title-cased with underscores as spaces (labels live in module files)."""
        self.assertEqual(_humanize_view_name("some_aux_view"), "Some Aux View")
        self.assertEqual(_humanize_view_name("selfcheckin"), "Selfcheckin")
        self.assertEqual(_humanize_view_name(""), "")


class FeaturedModuleSearchEntryTest(ProgramFrameworkTest):
    """Featured dashboard modules should be discoverable via the admin search.

    This guarantees:
      1. every featured module contributes at least one search entry, so
         featuring a module also makes it findable
      2. every search entry uses a known category, which
         catches stale labels that would create bogus search groups
    """

    # Dashboard section headers from directory.html; a featured module's search
    # entry must be categorized under one of these. The same strings live in
    # admin_search.py as the SEARCH_CATEGORY_* constants.
    _KNOWN_SECTIONS = frozenset([
        'Program Management and Settings',
        'Class Management and Scheduling',
        'Registration',
        'Participants and Communication',
        'Printables',
    ])
    # 'Other' is for manage tools that are searchable but not featured on the
    # dashboard
    _OTHER = 'Other'

    # Featured modules that intentionally produce no search entry
    _FEATURED_NOT_SEARCHABLE = frozenset(['ClassFlagModule'])

    def _featured_modules(self):
        """Featured modules we expect to be searchable: the isAdminPortalFeatured()
        whitelist as instantiated for this program, minus documented exceptions."""
        return [
            pmo for pmo in self.program.getModules()
            if pmo.isAdminPortalFeatured()
            and pmo.module.handler not in self._FEATURED_NOT_SEARCHABLE
        ]

    def _entry_ids_for(self, pmo):
        """Entry ids a module could produce, as `<module_type>_<view>` over all of
        its views. Mirrors how get_admin_search_entries() forms ids, so these can
        be matched against actual entry ids."""
        return {'%s_%s' % (pmo.module.module_type, v) for v in pmo.views}

    def test_every_featured_module_is_searchable(self):
        """Each featured module contributes at least one search entry."""
        entries = get_admin_search_entries(self.program)
        entry_ids = {e.id for e in entries}
        for pmo in self._featured_modules():
            # Searchable if any of the module's views produced an entry.
            module_ids = self._entry_ids_for(pmo)
            self.assertTrue(
                module_ids & entry_ids,
                "Featured module %s should contribute at least one search entry "
                "(views checked: %s)" % (pmo.module.handler, sorted(pmo.views)),
            )

    def test_all_entries_use_a_known_category(self):
        """Every search entry must use a known category.
        """
        allowed = self._KNOWN_SECTIONS | {self._OTHER}
        entries = get_admin_search_entries(self.program)
        for entry in entries:
            self.assertIn(
                entry.category, allowed,
                "%s uses category %r, which is not a valid search category"
                % (entry.id, entry.category),
            )

    def test_aux_endpoints_do_not_produce_entries(self):
        """Aux endpoints of featured modules must not appear as search results.

        get_admin_search_entry is called for every (tl, view) pair the module
        exposes, so each handler must return None for its non-main views to
        avoid broken search links (e.g. /manage/<prog>/grouptextfinal).
        """
        aux_views = [
            'create_autorule', 'batchclassregfinal', 'grouptextfinal',
            'deactivatefinal', 'usergroupfinal', 'userrecordsfinal',
            'start_testing', 'reset_testing', 'survey_manage',
        ]
        entries = get_admin_search_entries(self.program)
        entry_ids = {e.id for e in entries}
        for aux in aux_views:
            self.assertNotIn('manage_%s' % aux, entry_ids,
                             "Aux endpoint %r should not produce a search entry" % aux)
