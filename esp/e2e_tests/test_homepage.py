"""
E2E smoke test for the homepage.

Verifies that the Django dev server is running and the homepage
loads successfully.
"""


def test_homepage_loads(page, base_url):
    """Test that the homepage returns a successful response and renders."""
    response = page.goto(base_url + "/")
    assert response is not None
    assert response.status == 200


def test_homepage_has_title(page, base_url):
    """Test that the homepage has a non-empty title."""
    page.goto(base_url + "/")
    title = page.title()
    assert title is not None
    assert len(title) > 0


def test_homepage_has_content(page, base_url):
    """Test that the homepage renders visible content (not a blank page)."""
    page.goto(base_url + "/")
    body = page.locator("body")
    assert body.is_visible()
    # The body should contain some text content
    body_text = body.inner_text()
    assert len(body_text.strip()) > 0
