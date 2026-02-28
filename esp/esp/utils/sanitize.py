"""Server-side defense against base64 image data in HTML content.

When users paste images from clipboard (Word, Google Docs, screenshots) into
the Jodit WYSIWYG editor, the browser encodes them as data: URIs that can be
multi-megabyte strings. This module strips them before they reach the database.

See: https://github.com/learning-unlimited/ESP-Website/issues/3612
"""

import re
import logging

logger = logging.getLogger(__name__)

# Simple prefix patterns used with finditer + manual scanning for linear-time
# matching.  This avoids the nested-quantifier backtracking that CodeQL flags
# when a single regex contains multiple [^>]* or [^)]* groups.

_IMG_TAG_RE = re.compile(r'<img\b', re.IGNORECASE)

_CSS_DATA_URI_PREFIX_RE = re.compile(
    r'url\(\s*["\']?data:image/',
    re.IGNORECASE,
)

# Quick substring check used inside _strip_base64_img_tags to decide whether
# an <img> tag contains a data: URI src attribute.
_DATA_SRC_RE = re.compile(
    r'\bsrc\s*=\s*["\']data:',
    re.IGNORECASE,
)


def _strip_base64_img_tags(html):
    """Remove <img> tags whose src is a data: URI in linear time.

    Strategy: find each ``<img`` opening with a trivial regex, locate the
    closing ``>`` with ``str.find``, then test the bounded tag body for
    ``src="data:..."``.  No nested quantifiers are involved.
    """
    count = 0
    parts = []
    last = 0
    for m in _IMG_TAG_RE.finditer(html):
        start = m.start()
        if start < last:
            continue
        close = html.find('>', m.end())
        if close == -1:
            continue
        tag = html[start:close + 1]
        if _DATA_SRC_RE.search(tag):
            parts.append(html[last:start])
            last = close + 1
            count += 1
    parts.append(html[last:])
    return ''.join(parts), count


def _strip_css_data_uris(html):
    """Replace url(data:image/...) CSS patterns with url() in linear time."""
    count = 0
    parts = []
    last = 0
    for m in _CSS_DATA_URI_PREFIX_RE.finditer(html):
        start = m.start()
        if start < last:
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

    result, img_count = _strip_base64_img_tags(html)
    result, css_count = _strip_css_data_uris(result)

    total = img_count + css_count
    if total > 0:
        logger.warning(
            "Stripped %d base64 image(s) from content (%d chars removed)",
            total,
            len(html) - len(result),
        )

    return result, total
