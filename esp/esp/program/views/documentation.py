import os
import re
import mimetypes
import bleach
from functools import lru_cache
from docutils.core import publish_parts, publish_doctree
from docutils import nodes
from django.http import Http404, FileResponse, HttpResponseRedirect
from esp.utils.web import render_to_response

# Absolute path to docs/admin/ (four levels above this file:
# documentation.py -> views -> program -> esp -> esp -> devsite/docs/admin)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_ADMIN_ROOT = os.path.normpath(
    os.path.join(_THIS_DIR, '..', '..', '..', '..', 'docs', 'admin')
)

def _rst_to_html(rst_text):
    """Convert a reStructuredText string to an HTML body fragment safely."""
    parts = publish_parts(
        source=rst_text,
        writer_name='html',
        settings_overrides={
            'halt_level': 5,
            'report_level': 5,
            'file_insertion_enabled': False,
            'raw_enabled': False,
        },
    )
    raw_html = parts['body']

    # Sanitize using bleach to prevent XSS (CodeQL robustness)
    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'img', 'ul', 'ol', 'li',
        'strong', 'em', 'code', 'pre', 'blockquote', 'table', 'tr', 'td', 'th',
        'tbody', 'thead', 'span', 'div', 'br', 'hr', 'dl', 'dt', 'dd', 'tt'
    ]
    allowed_attributes = {
        '*': ['class', 'id', 'title'],
        'a': ['href', 'target'],
        'img': ['src', 'alt', 'width', 'height'],
    }
    allowed_protocols = ['http', 'https', 'mailto']

    return bleach.clean(
        raw_html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=allowed_protocols
    )

def _extract_rst_title(fpath):
    """Return the RST document title from a file, or None."""
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            rst_text = f.read()

        # Disable file insertion during parsing for safety
        doctree = publish_doctree(
            source=rst_text,
            settings_overrides={'file_insertion_enabled': False, 'raw_enabled': False}
        )
        titles = doctree.traverse(nodes.title)
        if titles:
            return titles[0].astext()
        return None
    except Exception:
        return None

@lru_cache(maxsize=1)
def _docs_nav():
    """Return a list of {'title', 'url_path'} dicts for the docs sidebar."""

    nav = []
    try:
        filenames = sorted(os.listdir(DOCS_ADMIN_ROOT))
    except OSError:
        return nav

    for fname in filenames:
        if not fname.endswith('.rst'):
            continue
        # Skip the admin README — the index page serves as the overview
        if fname == 'README.rst':
            continue
        fpath = os.path.join(DOCS_ADMIN_ROOT, fname)
        fallback = fname.replace('.rst', '').replace('_', ' ').title()
        title = _extract_rst_title(fpath) or fallback
        nav.append({
            'title': title,
            'url_path': fname,
        })
    # Release notes index
    nav.append({
        'title': 'Release Notes',
        'url_path': 'releases/README.rst',
    })
    return nav

def _latest_release():
    """Return (label, html) for the most recent release notes."""
    releases_dir = os.path.join(DOCS_ADMIN_ROOT, 'releases')
    try:
        subdirs = [
            d for d in os.listdir(releases_dir)
            if os.path.isdir(os.path.join(releases_dir, d)) and d.isdigit()
        ]
    except OSError:
        return None, None
    if not subdirs:
        return None, None
    latest = str(max(int(d) for d in subdirs))
    rst_path = os.path.join(releases_dir, latest, 'README.rst')
    try:
        with open(rst_path, 'r', encoding='utf-8') as f:
            rst_text = f.read()
    except OSError:
        return None, None
    # Extract title line for the label
    label = 'SR{0}'.format(latest)
    lines = rst_text.splitlines()
    for line in lines:
        line = line.strip()
        if line and not set(line).issubset(set('= ')):
            label = line.strip()
            break

    # Truncate to give a preview (skip table of contents, stop at Changelog or after 15 lines)
    preview_lines = []
    skip_contents = False

    for i, line in enumerate(lines):
        if line.startswith('.. contents::'):
            skip_contents = True
            continue
        if skip_contents and line.startswith('      '): # skip indented TOC items
            continue
        else:
            skip_contents = False

        if line.startswith('Changelog') or len(preview_lines) >= 15:
            break
        preview_lines.append(line)

    preview_lines.append("")
    preview_lines.append("`\u2192 Read the full %s </manage/docs/releases/%s/README.rst>`__" % (label, latest))

    return label, _rst_to_html("\n".join(preview_lines))

def manage_docs(request, doc_path=None):
    """Render admin documentation pages embedded within the website."""

    doc_html = None
    doc_title = 'Admin Documentation'

    if doc_path:
        # Strip trailing slash so /releases/16/ is treated as /releases/16
        doc_path = doc_path.rstrip('/')
        if not doc_path:
            raise Http404
        # Redirect index.html to the docs root
        if doc_path == 'index.html':
            return HttpResponseRedirect('/manage/docs/')
        # Security: validate path only contains safe characters (whitelist)
        # before joining with DOCS_ADMIN_ROOT to prevent path traversal.
        if not re.match(r'^[A-Za-z0-9_./-]+$', doc_path) or '..' in doc_path:
            raise Http404
        # Resolve the full path and confirm it stays inside DOCS_ADMIN_ROOT
        requested = os.path.realpath(os.path.join(DOCS_ADMIN_ROOT, doc_path))
        if not requested.startswith(DOCS_ADMIN_ROOT + os.sep):
            raise Http404
        if os.path.isdir(requested):
            requested = os.path.join(requested, 'README.rst')
        if not os.path.isfile(requested):
            raise Http404

        # If the requested file is not RST (e.g., an image), serve it directly
        if not requested.endswith('.rst'):
            content_type, _ = mimetypes.guess_type(requested)
            if not content_type:
                content_type = 'application/octet-stream'
            try:
                return FileResponse(open(requested, 'rb'), content_type=content_type)
            except OSError:
                raise Http404

        # Parse RST normally
        try:
            with open(requested, 'r', encoding='utf-8') as f:
                rst_text = f.read()
        except OSError:
            raise Http404
        doc_html = _rst_to_html(rst_text)

        # Consistent title extraction using our helper
        doc_title = _extract_rst_title(requested) or 'Admin Documentation'

    latest_release_label, latest_release_html = _latest_release()

    context = {
        'doc_nav': _docs_nav(),
        'doc_html': doc_html,
        'doc_title': doc_title,
        'doc_path': doc_path,
        'latest_release_label': latest_release_label,
        'latest_release_html': latest_release_html,
    }
    return render_to_response('program/manage_docs.html', request, context)
