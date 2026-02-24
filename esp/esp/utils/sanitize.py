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

# Match the prefix of url(data:image/...) patterns in CSS.
# Used with finditer + str.find(')') for linear-time matching,
# avoiding polynomial backtracking from a single regex with [^)]*\).
_CSS_DATA_URI_PREFIX_RE = re.compile(
    r'url\(\s*["\']?data:image/',
    re.IGNORECASE,
)


def _strip_css_data_uris(html):
    """Replace url(data:image/...) CSS patterns with url() in linear time."""
    count = 0
    parts = []
    last = 0
    for m in _CSS_DATA_URI_PREFIX_RE.finditer(html):
        start = m.start()
        if start < last:
            # This match overlaps with a previous replacement; skip it
            continue
        close = html.find(')', m.end())
        if close == -1:
            continue
        parts.append(html[last:start])
        parts.append('url()')
        last = close + 1
        count += 1
    parts.append(html[last:])
    return ''.join(parts), count


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

    img_count = [0]

    def _replace_img(_match):
        img_count[0] += 1
        return ''

    result = _BASE64_IMG_RE.sub(_replace_img, html)
    result, css_count = _strip_css_data_uris(result)

    total = img_count[0] + css_count
    if total > 0:
        logger.warning(
            "Stripped %d base64 image(s) from content (%d chars removed)",
            total,
            len(html) - len(result),
        )

    return result, total
