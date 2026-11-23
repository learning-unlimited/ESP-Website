"""
Build an inventory of every page on the site and who should be able to see it.

The inventory has one row per URL (or URL pattern) and comes from three places:

- the Django URLconf (every non-program-module view, including the admin site)
- program module handlers (every @main_call / @aux_call view, per program)
- QSD pages stored in the database

Each row records the access decorators on the view and the roles they imply,
so the same file serves as a manual testing checklist and as input to the
browser crawl in deploy/release_testing/crawl.py.

Building the inventory only reads from the database.
"""

import ast
import inspect
import re
from collections import namedtuple
from functools import lru_cache

from django.urls import URLPattern, URLResolver, get_resolver

ROLES = ['anonymous', 'student', 'teacher', 'volunteer', 'onsite', 'admin']
LOGGED_IN = ['student', 'teacher', 'volunteer', 'onsite', 'admin']

# Access decorators and the roles they let through. Admins pass every check.
DECORATOR_ROLES = {
    'needs_admin': ['admin'],
    'admin_required': ['admin'],
    'needs_onsite': ['onsite', 'admin'],
    'needs_onsite_no_switchback': ['onsite', 'admin'],
    'needs_teacher': ['teacher', 'admin'],
    'needs_student': ['student', 'admin'],
    'needs_student_in_grade': ['student', 'admin'],
    'needs_account': LOGGED_IN,
    'login_required': LOGGED_IN,
    'LoginRequiredMixin': LOGGED_IN,
    'staff_member_required': ['admin'],
    'anonymous_only': ['anonymous'],
}
# usercheck_usetl picks the role from the URL's first segment
TL_ROLES = {
    'learn': ['student', 'admin'],
    'teach': ['teacher', 'admin'],
    'manage': ['admin'],
    'onsite': ['onsite', 'admin'],
}
# Decorators whose checks this module cannot translate into roles
CUSTOM_ACCESS = {'user_passes_test', 'user_is_staff', 'meets_cap', 'meets_grade'}
DEADLINE_DECORATORS = {'meets_deadline', 'meets_any_deadline'}
NO_DECORATOR = 'no access decorator found'

# Views a GET request changes state in, or that end the crawler's session.
# The crawl skips these; they stay in the inventory for manual testing.
UNSAFE_VIEW_WORDS = (
    'logout', 'signout', 'morph', 'switchback', 'switch_back', 'start_testing',
    'delete', 'remove', 'deactivate', 'activate', 'unenroll', 'unregister',
    'flushcache', 'clear', 'reset', 'cancel', 'approve', 'reject', 'accept',
    'undo', 'purge', 'expire', 'checkin', 'checkout', 'mark', 'attend',
    'testing', 'recompile',
)

# Views flagged by writes_on_get() whose GET writes someone has checked are
# harmless, so the crawl still visits them. Key: 'Handler.view' or 'module.view'.
GET_WRITES_REVIEWED = {
    'StudentRegProfileModule.profile': "copies a legacy e_mail field into the user's own contact info",
    'TeacherRegProfileModule.profile': "copies a legacy e_mail field into the user's own contact info",
}

FIELDS = [
    'area', 'url', 'url_pattern', 'tl', 'module', 'view', 'call_type', 'kind',
    'decorators', 'expected_roles', 'deadline_gated', 'writes_on_get',
    'crawlable', 'skip_reason', 'source', 'description',
]
# AJAX/JSON views that expect query parameters; a bare GET often fails
ENDPOINT_RE = re.compile(r'ajax|json|(^|[_/-])api([_/-]|$)|check-|autocomplete', re.I)


def _decorator_name(node):
    """'needs_admin' for @needs_admin, @esp.x.needs_admin, @needs_admin(...)
    or @method_decorator(needs_admin)."""
    if isinstance(node, ast.Call):
        if _decorator_name(node.func) == 'method_decorator' and node.args:
            return _decorator_name(node.args[0])
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ast.unparse(node)


@lru_cache(maxsize=None)
def _parse_file(path):
    with open(path, encoding='utf-8') as f:
        return ast.parse(f.read(), filename=path)


# What the inventory knows about a view's source code
ViewInfo = namedtuple('ViewInfo', 'decorators source doc writes')
NO_INFO = ViewInfo([], '', '', [])

# Method calls that look like database writes
WRITE_CALLS = {
    'delete', 'save', 'bulk_create', 'bulk_update', 'update_or_create',
    'makeRole', 'makeAdmin', 'set_password', 'preregister_student',
    'unpreregister_student', 'send_mail', 'send_email',
}


def _write_call(node):
    """'x.save()' if node is a call that looks like a database write, else None."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    name, target = node.func.attr, node.func.value
    if (name in WRITE_CALLS
            or (name == 'create' and 'objects' in ast.unparse(target))
            # queryset.filter(...).update(...)
            or (name == 'update' and isinstance(target, ast.Call))):
        return ast.unparse(node.func)[:60] + '()'
    return None


def writes_on_get(func_node):
    """Calls in a view that look like database writes and aren't behind a POST check.

    A heuristic: it reads the view's own body, not the functions it calls,
    so an empty result does not prove a GET is safe.
    """
    found = []

    def check(expr):
        for node in ast.walk(expr):
            call = _write_call(node)
            if call:
                found.append(call)

    def scan(stmts):
        """Scan a block. Returns True if the rest of the block only runs on POST."""
        for st in stmts:
            test = ast.unparse(st.test) if isinstance(st, ast.If) else ''
            if 'POST' in test or "'GET'" in test:
                get_branch_first = (test.startswith('not ') or "!= 'POST'" in test
                                    or '!= "POST"' in test or "== 'GET'" in test)
                if get_branch_first:
                    scan(st.body)
                    # `if not POST: return ...` leaves only POST code after it
                    if st.body and isinstance(st.body[-1], (ast.Return, ast.Raise)):
                        return True
                    scan(st.orelse)
                else:
                    scan(st.orelse)
                continue
            blocks = [getattr(st, f, None) or [] for f in ('body', 'orelse', 'finalbody')]
            blocks += [h.body for h in getattr(st, 'handlers', [])]
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or not any(blocks):
                check(st)
                continue
            for attr in ('test', 'iter'):
                if getattr(st, attr, None) is not None:
                    check(getattr(st, attr))
            for item in getattr(st, 'items', []):
                check(item.context_expr)
            for block in blocks:
                scan(block)
        return False

    scan(func_node.body)
    return list(dict.fromkeys(found))


def _info_from_node(node, path):
    doc = (ast.get_docstring(node) or '').strip().splitlines()
    return ViewInfo(
        decorators=[ast.unparse(d) for d in node.decorator_list],
        source=f'{_relpath(path)}:{node.lineno}',
        doc=doc[0] if doc else '',
        # Only ESP's own code is checked for writes
        writes=writes_on_get(node) if '/esp/esp/' in path else [],
    )


def _function_info(func):
    """ViewInfo for a view function."""
    func = inspect.unwrap(func)
    func = getattr(func, 'method', func)
    try:
        path = inspect.getsourcefile(func)
        _, lineno = inspect.getsourcelines(func)
    except (TypeError, OSError):
        return NO_INFO
    for node in ast.walk(_parse_file(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func.__name__:
            # getsourcelines starts at the first decorator
            if min([d.lineno for d in node.decorator_list] + [node.lineno]) == lineno:
                return _info_from_node(node, path)
    return NO_INFO._replace(source=f'{_relpath(path)}:{lineno}')


def _method_info(cls, name):
    """ViewInfo for a method found by name on cls or a base class.

    ESP's access decorators don't all keep a reference to the function they
    wrap, so the source is found from the class instead.
    """
    for klass in cls.__mro__:
        if name not in klass.__dict__:
            continue
        try:
            path = inspect.getsourcefile(klass)
        except TypeError:
            break
        for node in ast.walk(_parse_file(path)):
            if isinstance(node, ast.ClassDef) and node.name == klass.__name__:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == name:
                        return _info_from_node(item, path)
                    # An alias such as `deadlines = deadline_management`
                    if (isinstance(item, ast.Assign) and isinstance(item.value, ast.Name)
                            and item.value.id != name
                            and any(isinstance(t, ast.Name) and t.id == name for t in item.targets)):
                        return _method_info(cls, item.value.id)
        break
    return NO_INFO


def _relpath(path):
    """Path relative to the repository, or to site-packages for libraries."""
    for marker, prefix in (('/esp/esp/', 'esp/esp/'), ('/site-packages/', '')):
        if marker in path:
            return prefix + path.split(marker, 1)[1]
    return path


def decorator_names(decorators):
    return [_decorator_name(ast.parse(d, mode='eval').body) for d in decorators]


def expected_roles(decorators, tl=None):
    """Roles that should get the page, from a view's access decorators.

    Returns (roles, note). roles is None when the check is custom code that
    the crawl cannot predict. With no access decorator every role is
    expected, though the view may still check access in its body.
    """
    roles = list(ROLES)
    custom = []
    found = False
    for name in decorator_names(decorators):
        if name in DECORATOR_ROLES:
            roles = [r for r in roles if r in DECORATOR_ROLES[name]]
        elif name == 'usercheck_usetl' and tl in TL_ROLES:
            roles = [r for r in roles if r in TL_ROLES[tl]]
        elif name in CUSTOM_ACCESS:
            custom.append(name)
        else:
            continue
        found = True
    if custom:
        return None, 'custom check: ' + ', '.join(custom)
    return roles, '' if found else NO_DECORATOR


def _unsafe_reason(view_name, writes=(), key=''):
    """Why the crawl should not GET this view, or '' if nothing suggests a write."""
    lowered = view_name.lower()
    for word in UNSAFE_VIEW_WORDS:
        if word in lowered:
            return f'view name contains "{word}"; may change data on GET'
    if writes and key not in GET_WRITES_REVIEWED:
        return 'may write to the database on GET (see writes_on_get)'
    return ''


def _kind(*names):
    return 'endpoint' if any(ENDPOINT_RE.search(n) for n in names if n) else 'page'


def _row(**kwargs):
    row = {field: '' for field in FIELDS}
    row.update(kwargs)
    return row


# ---------------------------------------------------------------------------
# Django URLconf
# ---------------------------------------------------------------------------

# Patterns handled elsewhere in the inventory, or not pages at all
URLCONF_SKIP = (
    re.compile(r'^\(onsite\|manage\|teach\|learn\|volunteer\|json\)'),  # program modules
    re.compile(r'^\(\?P<url>\.\*\)\\\.html'),                          # QSD pages
    re.compile(r'^(media|static)/'),                                     # static files
    re.compile(r'^__debug__/'),
    re.compile(r'^javascript_tests'),
)


def _walk(patterns, prefix=''):
    for p in patterns:
        piece = str(p.pattern).lstrip('^')
        if isinstance(p, URLResolver):
            yield from _walk(p.url_patterns, prefix + piece)
        elif isinstance(p, URLPattern):
            yield prefix + piece, p


def _concrete_url(pattern, fill):
    """Turn a URL pattern into a URL, filling named groups from `fill`.

    Returns None if the pattern has parts that cannot be filled.
    """
    s = pattern.replace('^', '').replace('$', '')
    # path() converters, e.g. <int:pk>
    s = re.sub(r'(?<!\?P)<(?:\w+:)?(\w+)>', lambda m: fill.get(m.group(1), '\0'), s)
    # Optional literal groups such as (success)? are left out, and
    # alternatives such as (faq|faq\.html) take the first choice
    s = re.sub(r'\((?!\?)[^()]*\)\?', '', s)
    s = re.sub(r'\((?!\?)([\w\\.-]+)(?:\|[\w\\.|-]+)\)', r'\1', s)

    # Named regex groups, innermost first
    def named(m):
        return fill.get(m.group(1), '\0')
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\(\?P<(\w+)>[^()]*\)', named, s)
    # Optional trailing pieces such as (?:/(?P<doc_path>.*))? or /?
    s = re.sub(r'\(\?:[^()]*\)\?', '', s)
    s = s.replace('/?', '/').replace('\\.', '.').replace('\\-', '-')
    if '\0' in s or re.search(r'[()\[\]*+?|\\{}]', s):
        return None
    return re.sub(r'/+', '/', '/' + s)


def urlconf_rows(program=None):
    fill = {}
    if program is not None:
        fill = {'program_type': program.program_type, 'program_term': program.program_instance,
                'one': program.program_type, 'two': program.program_instance}
    rows = []
    seen = set()
    for pattern, p in _walk(get_resolver().url_patterns):
        if any(r.search(pattern) for r in URLCONF_SKIP) or pattern in seen:
            continue
        seen.add(pattern)
        callback = p.callback
        view_name = getattr(callback, '__name__', '')
        view_class = getattr(callback, 'view_class', None)
        module = getattr(callback, '__module__', '')
        # ESP's own views under /admin/ check access themselves
        is_admin_site = pattern.startswith('admin/') and not module.startswith('esp.')
        if view_class is not None:
            view_name = view_class.__name__
            info = _function_info(view_class.dispatch)
            # Mixins such as LoginRequiredMixin are listed with the decorators
            info = info._replace(decorators=info.decorators + [
                c.__name__ for c in view_class.__mro__ if c.__name__ in DECORATOR_ROLES])
            if not info.source:
                info = info._replace(source=_relpath(inspect.getsourcefile(view_class) or ''))
        else:
            info = _function_info(callback)
        decorators = info.decorators
        if is_admin_site and pattern == 'admin/login/':
            roles, note = ROLES, ''
        elif is_admin_site:
            roles, note = ['admin'], 'Django admin site (staff only)'
        else:
            roles, note = expected_roles(decorators)
        url = _concrete_url(pattern, fill)
        # Two patterns can produce the same URL; Django serves the first
        if url is not None:
            if url in seen:
                continue
            seen.add(url)
        if url is None:
            skip = 'URL needs arguments'
        elif 'RedirectView' in view_name:
            skip = 'redirect'
        elif 'require_POST' in decorator_names(decorators):
            skip = 'POST only'
        else:
            skip = _unsafe_reason(url, info.writes, f'{module}.{view_name}')
        rows.append(_row(
            area=pattern.split('/')[0] or 'home',
            url=url or '',
            url_pattern=pattern,
            view=f'{module}.{view_name}',
            call_type='urlconf',
            kind=_kind(pattern, view_name),
            decorators='; '.join(decorators),
            expected_roles=', '.join(roles) if roles is not None else '',
            writes_on_get=', '.join(info.writes),
            crawlable='no' if skip else 'yes',
            skip_reason=skip or note,
            source=info.source,
            description=info.doc,
        ))
    return rows


# ---------------------------------------------------------------------------
# Program modules
# ---------------------------------------------------------------------------

def handler_views(handler_class):
    """(view name, 'Main Call' | 'Aux Call') for each view a module handler defines."""
    from esp.program.modules.base import ProgramModuleObj
    base = set(dir(ProgramModuleObj))
    views = []
    for key in sorted(set(dir(handler_class)) - base):
        item = getattr(handler_class, key, None)
        tag = getattr(item, 'call_tag', None)
        if callable(item) and tag in ('Main Call', 'Aux Call'):
            views.append((key, tag))
    return views


def module_rows(programs=()):
    """One row per (module view, program); one template row if a module is in no given program."""
    from esp.program.models import ProgramModule
    enabled = {prog: set(prog.program_modules.values_list('id', flat=True)) for prog in programs}
    rows = []
    for pm in ProgramModule.objects.order_by('module_type', 'handler'):
        try:
            cls = pm.getPythonClass()
        except ProgramModule.CannotGetClassException:
            continue
        tl = pm.module_type
        for view, tag in handler_views(cls):
            info = _method_info(cls, view)
            roles, note = expected_roles(info.decorators, tl)
            names = set(decorator_names(info.decorators))
            base = dict(
                area=tl, tl=tl, module=f'{pm.admin_title} ({pm.handler})', view=view,
                url_pattern=f'/{tl}/<program>/{view}',
                call_type='main' if tag == 'Main Call' else 'aux',
                kind='endpoint' if tl == 'json' else _kind(view),
                decorators='; '.join(info.decorators),
                expected_roles=', '.join(roles) if roles is not None else '',
                deadline_gated='yes' if names & DEADLINE_DECORATORS else '',
                writes_on_get=', '.join(info.writes),
                source=info.source, description=info.doc,
            )
            key = f'{pm.handler}.{view}'
            unsafe = _unsafe_reason(view, info.writes, key)
            if not unsafe and key in GET_WRITES_REVIEWED:
                note = 'GET write reviewed: ' + GET_WRITES_REVIEWED[key]
            progs = [prog for prog in programs if pm.id in enabled[prog]]
            if not progs:
                rows.append(_row(**base, crawlable='no',
                                 skip_reason='module not enabled in the inventoried program(s)'))
            for prog in progs:
                rows.append(_row(**base, url=f'/{tl}/{prog.url}/{view}',
                                 crawlable='no' if unsafe else 'yes',
                                 skip_reason=unsafe or note))
    return rows


# ---------------------------------------------------------------------------
# QSD pages
# ---------------------------------------------------------------------------

def qsd_rows():
    from esp.qsd.models import QuasiStaticData
    rows = []
    urls = (QuasiStaticData.objects.exclude(url__startswith='learn:')
            .exclude(url__startswith='teach:').values_list('url', flat=True).distinct())
    for url in sorted(set(urls)):
        # Inline QSD blocks have names, not pages
        if not url or ':' in url or ' ' in url:
            continue
        rows.append(_row(
            area='qsd', url=f'/{url}.html', url_pattern='/<url>.html',
            view='esp.qsd.views.qsd', call_type='qsd', kind='page',
            # The QSD view only lets admins read pages under manage/
            expected_roles='admin' if url.startswith('manage/') else ', '.join(ROLES), crawlable='yes',
            source='database (QuasiStaticData)',
        ))
    return rows


def build_inventory(programs=(), include_qsd=True):
    rows = urlconf_rows(programs[0] if programs else None)
    rows += module_rows(programs)
    if include_qsd:
        rows += qsd_rows()
    return rows
