"""Filter to convert text to markdown

Copied and simplified for our use case from the Django 1.4 version of the
django.contrib.markup app:
  https://github.com/django/django/blob/stable/1.4.x/django/contrib/markup/templatetags/markup.py
This app has been deprecated by Django for security reasons.
However, we still need to use it with higher versions of Django,
and we are not as concerned about security since the Markdown code
is only entered by "trusted" users.  The code is also simpler for us since we
pin to a given version of markdown, and don't use markdown extensions.
"""

from __future__ import absolute_import
import re

from django import template
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.safestring import mark_safe

# Can't conflict with the `markdown` filter name.
import markdown as md
import bleach

register = template.Library()

# An HTML comment, paired the way browsers pair them (HTML spec "comment
# start state" onward): '<!-->' and '<!--->' are complete empty comments,
# otherwise the first '-->' (or '--!>') closes it. Group 1 is set only when
# it's terminated -- an unterminated '<!--' runs to the end of the text.
_COMMENT_RE = re.compile(r'<!--(?:-?>|.*?(--!?>)|.*\Z)', re.S)
# The stand-in comments _stash_comments() swaps in, either as Markdown
# passes them through (raw HTML) or as it escapes them (inside a code block).
_PLACEHOLDER = '<!--esp-md-comment-%d-->'
_PLACEHOLDER_RE = re.compile(r'<!--esp-md-comment-(\d+)-->|&lt;!--esp-md-comment-(\d+)--&gt;')


def _stash_comments(text):
    """Swap each HTML comment in `text` for a short stand-in comment.

    Markdown 2.3.1 mangles comments: one containing blank lines whose first
    paragraph ends in '>' (e.g. a commented-out chunk of Jodit HTML ending in
    '</p>'), or one starting inside a block-level tag like '<p>', gets split
    up and its closing '-->' escaped to '--&gt;' -- so the browser sees an
    unterminated comment that swallows the rest of the page, including the
    QSD's own edit controls. A short single-line comment is handled
    correctly in every position, and keeps Markdown's raw-HTML block
    detection behaving exactly as it would with the original comment there.

    An unterminated '<!--' is closed at the end of `text`, so it hides only
    the rest of this text rather than the rest of the page.
    """
    comments = []

    def stash(match):
        comment = match.group(0)
        if match.group(1) is None and not re.match(r'<!---?>\Z', comment):
            comment += '-->'
        comments.append(comment)
        return _PLACEHOLDER % (len(comments) - 1)

    return _COMMENT_RE.sub(stash, text), comments


def _restore_comments(html, comments):
    def restore(match):
        if match.group(1) is not None:
            return comments[int(match.group(1))]
        # Markdown escaped the stand-in (e.g. it was in a code block), so it
        # displays as text there -- escape the original to match.
        return escape(comments[int(match.group(2))])

    return _PLACEHOLDER_RE.sub(restore, html)


def render_markdown(text):
    """Runs Markdown over `text`, passing HTML comments through verbatim."""
    stashed, comments = _stash_comments(force_text(text))
    return _restore_comments(md.markdown(stashed), comments)


@register.filter(is_safe=True)
def markdown(value):
    """Runs Markdown over a given value."""
    return mark_safe(render_markdown(value))


# Tags allowed by `sanitize_html`: bleach's defaults (a, abbr, acronym, b,
# blockquote, code, em, i, li, ol, strong, ul) plus simple formatting.
_SANITIZE_TAGS = frozenset(bleach.sanitizer.ALLOWED_TAGS) | {'br', 'p', 'u'}


@register.filter(is_safe=True)
def sanitize_html(value):
    """Renders `value` as HTML, keeping only a small set of safe tags.

    For text that the editor treats as HTML but that untrusted users (e.g.
    teachers building custom forms) can write, so it can't simply be marked
    |safe. Disallowed tags are stripped, as for class QSDs.
    """
    return mark_safe(bleach.clean(force_text(value), tags=_SANITIZE_TAGS, strip=True))
