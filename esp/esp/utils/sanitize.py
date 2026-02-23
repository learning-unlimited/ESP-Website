"""Server-side defense against base64 image data in HTML content.

When users paste images from clipboard (Word, Google Docs, screenshots) into
the Jodit WYSIWYG editor, the browser encodes them as data: URIs that can be
multi-megabyte strings. This module strips them before they reach the database.

See: https://github.com/learning-unlimited/ESP-Website/issues/3612
"""

import re
import logging

logger = logging.getLogger(__name__)

# Match <img> tags whose src attribute is a data: URI.
# Handles: single/double quotes, attributes before/after src, self-closing tags.
# re.DOTALL lets . match newlines inside the tag.
_BASE64_IMG_RE = re.compile(
    r'<img\b[^>]*\bsrc\s*=\s*["\']data:[^"\']*["\'][^>]*/?>',
    re.IGNORECASE | re.DOTALL,
)

# Match url(data:image/...) in inline CSS (e.g. background-image).
# Handles: optional quotes around the URL, whitespace after (.
_CSS_DATA_URI_RE = re.compile(
    r'url\(\s*["\']?data:image/[^)]*\)',
    re.IGNORECASE,
)


def strip_base64_images(html):
    """Strip base64 data URIs from HTML content.

    Removes:
    - ``<img src="data:...">`` tags entirely
    - ``url(data:image/...)`` in CSS (replaced with ``url()``)

    Args:
        html: HTML string to sanitize. None and empty string are safe no-ops.

    Returns:
        Tuple of ``(sanitized_html, count_removed)`` where *count_removed*
        is the total number of base64 occurrences that were stripped.
    """
    if not html or 'data:' not in html:
        return html, 0

    count = [0]

    def _replace_img(match):
        count[0] += 1
        return ''

    def _replace_css(match):
        count[0] += 1
        return 'url()'

    result = _BASE64_IMG_RE.sub(_replace_img, html)
    result = _CSS_DATA_URI_RE.sub(_replace_css, result)

    if count[0] > 0:
        logger.warning(
            "Stripped %d base64 image(s) from content (%d chars removed)",
            count[0],
            len(html) - len(result),
        )

    return result, count[0]
