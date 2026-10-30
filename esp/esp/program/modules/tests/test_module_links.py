"""
Tests for the HTML link helpers on ``ProgramModuleObj``:
``makeLink``, ``makeSetupLink`` and ``makeButtonLink``.

These helpers build ``<a>`` tags from module titles and docs text and return
them as safe HTML (templates render them without further escaping, e.g.
``{% autoescape off %}{{ module.makeLink }}{% endautoescape %}``).  The values
interpolated into the markup must therefore be escaped by the helpers
themselves.  The tests parse the generated HTML and check what a browser
would see: exactly one ``<a>`` tag, whose ``title`` attribute and text equal
the original, unescaped strings.
"""

from html.parser import HTMLParser

from django.utils.safestring import SafeString

from esp.program.tests import ProgramFrameworkTest


class _LinkParser(HTMLParser):
    """Collect start tags (with decoded attributes) and text from an HTML snippet."""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def _parse(html):
    parser = _LinkParser()
    parser.feed(str(html))
    parser.close()
    return parser


# Text that would break out of a double-quoted attribute or inject markup if
# it were interpolated without escaping.
NASTY = 'Say "hello" & it\'s <b>bold</b> <img src=x onerror=alert(1)>'


class ModuleLinkEscapingTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        modules = self.program.getModules()
        self.manage_module = self._first_of_type(modules, 'manage')
        self.learn_module = self._first_of_type(modules, 'learn')

    def _first_of_type(self, modules, module_type):
        for mod in modules:
            if mod.module.module_type == module_type:
                return mod
        self.fail(f"Test program has no '{module_type}' module")

    def _assert_single_link(self, html, title_attr=None, text=None):
        """The output is safe HTML containing exactly one <a> tag and nothing else."""
        self.assertIsInstance(html, SafeString)
        parsed = _parse(html)
        self.assertEqual([tag for tag, _ in parsed.tags], ['a'],
                         msg=f"Unexpected markup was injected: {html!r}")
        attrs = parsed.tags[0][1]
        if title_attr is not None:
            self.assertEqual(attrs.get('title'), title_attr)
        if text is not None:
            self.assertEqual(''.join(parsed.text).strip(), text)
        return attrs

    # -- makeLink -----------------------------------------------------------

    def test_make_link_plain_title_format_unchanged(self):
        """Ordinary titles render exactly as before (tests/existence.py matches this shape)."""
        mod = self.learn_module
        mod.link_title = 'Plain Title'
        self.assertEqual(
            mod.makeLink(),
            f'<a href="{mod.get_full_path()}" title="Plain Title" class="vModuleLink" >Plain Title</a>')

    def test_make_link_escapes_title(self):
        mod = self.learn_module
        mod.link_title = NASTY
        self._assert_single_link(mod.makeLink(), title_attr=NASTY, text=NASTY)

    def test_make_link_manage_escapes_docs_in_title_attribute(self):
        mod = self.manage_module
        mod.doc = NASTY
        attrs = self._assert_single_link(mod.makeLink(), title_attr=NASTY)
        self.assertEqual(attrs.get('class'), 'vModuleLink')

    def test_make_link_manage_docs_have_no_stray_backslash(self):
        """A single quote used to be rendered as a literal ``\\'`` in the tooltip."""
        mod = self.manage_module
        mod.doc = "it's fine"
        self.assertNotIn('\\', str(mod.makeLink()))
        self._assert_single_link(mod.makeLink(), title_attr="it's fine")

    def test_make_link_manage_preserves_multiline_docs(self):
        mod = self.manage_module
        mod.doc = 'line one\nline two'
        self._assert_single_link(mod.makeLink(), title_attr='line one\nline two')

    # -- makeSetupLink ------------------------------------------------------

    def test_make_setup_link_escapes_title(self):
        mod = self.manage_module
        mod.setup_title = NASTY
        self._assert_single_link(mod.makeSetupLink(), title_attr=NASTY, text=NASTY)

    def test_make_setup_link_escapes_path(self):
        mod = self.manage_module
        mod.setup_path = 'foo"><script>alert(1)</script>'
        attrs = self._assert_single_link(mod.makeSetupLink())
        self.assertTrue(attrs['href'].endswith('foo"><script>alert(1)</script>'))

    # -- makeButtonLink -----------------------------------------------------

    def test_make_button_link_manage_escapes_docs_and_title(self):
        mod = self.manage_module
        mod.doc = NASTY
        mod.module.link_title = NASTY
        self._assert_single_link(mod.makeButtonLink(), title_attr=NASTY, text=NASTY)

    def test_make_button_link_non_manage_escapes_title(self):
        mod = self.learn_module
        mod.module.link_title = NASTY
        html = mod.makeButtonLink()
        self.assertIsInstance(html, SafeString)
        parsed = _parse(html)
        # The button markup is a div wrapper containing one <a> and one inner <div>;
        # the injected <b>/<img> must not appear as extra elements.
        self.assertEqual([tag for tag, _ in parsed.tags], ['div', 'a', 'div'])
        self.assertEqual(''.join(parsed.text).strip(), NASTY)
