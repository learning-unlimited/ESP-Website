#!/usr/bin/env python3
"""
Visit every crawlable page in a URL inventory as each role, in a real browser.

    python deploy/release_testing/crawl.py \\
        --inventory inventory.json --sessions sessions.json \\
        --base-url http://localhost:8000 --out crawl-results

For each (URL, role) it records the HTTP status, where the page ended up,
JavaScript errors, failed asset requests and a screenshot, then compares the
outcome with the roles the inventory expects. It writes results.json,
results.csv and report.html to --out. With --compare it also lists what
changed since an earlier run (e.g. the previous release on the same data).

The crawl only sends GET requests: it blocks any other request a page makes
unless --allow-post is given. Even so, only point it at a disposable copy of
a site. Inventory and sessions come from `manage.py url_inventory` and
`manage.py crawl_sessions`; see docs/dev/release_testing.rst.

Needs only Playwright (deploy/release_testing/requirements.txt), not Django.
"""

import argparse
import asyncio
import csv
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter
from urllib.parse import urlparse

ROLES = ['anonymous', 'student', 'teacher', 'volunteer', 'onsite', 'admin']
LOGIN_PATHS = ('/accounts/login', '/myesp/login', '/admin/login')
LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}
# Logged-in page used to check a role's session survived the crawl
SESSION_CANARY = '/myesp/accountmanage/'

# Text from ESP's templates/errors/program/*.html pages, which return HTTP 200.
# A chapter's template overrides can change this text; the crawl then
# reports those pages as "ok".
DENIED_MARKERS = (
    'you are not an administrator of this program',
    'The user account is not a student',
    'you did not register as a teacher',
    'Sorry, you are not authorized to access this page',
)
CLOSED_MARKERS = (
    'is not currently open, possibly because you are either too early or too late',
    'Not in the correct grade for this program',
    'the program to which you are trying to register is full',
)

# Most serious first; a result's verdict is the first that applies
VERDICTS = ['server-error', 'unexpected-allow', 'not-found', 'unexpected-deny',
            'endpoint-error', 'js-error', 'asset-error', 'closed', 'ok', 'info']
VERDICT_HELP = {
    'server-error': 'HTTP 5xx or the page did not load',
    'unexpected-allow': 'role got the page but its access decorators say it should not',
    'not-found': 'HTTP 404 for a role that should see the page',
    'unexpected-deny': 'role was refused or sent to log in although it should see the page '
                       '(lower priority when the inventory found no access decorator)',
    'endpoint-error': 'AJAX/JSON endpoint returned 5xx to a bare GET; often a missing '
                      'parameter, but it should answer 400 instead',
    'js-error': 'page loaded but logged JavaScript errors',
    'asset-error': 'page loaded but a script, stylesheet or image failed',
    'closed': 'deadline, grade or capacity page (check the program setup)',
    'ok': 'loaded as expected',
    'info': 'loaded; access is decided by custom code so nothing to compare',
}
FIELDS = ['verdict', 'url', 'role', 'kind', 'outcome', 'status', 'final_url', 'title',
          'expected_roles', 'js_errors', 'asset_errors', 'blocked_requests',
          'screenshot', 'area', 'module', 'view', 'skip_reason', 'source']


def classify(status, requested_path, final_path, text):
    """What happened when the page was requested, from the role's point of view."""
    if status is None:
        return 'load-failed'
    if status >= 500:
        return 'server-error'
    if status == 404:
        return 'not-found'
    if status in (401, 403):
        return 'denied'
    if final_path.startswith(LOGIN_PATHS) and not requested_path.startswith(LOGIN_PATHS):
        return 'login-required'
    if any(m in text for m in DENIED_MARKERS):
        return 'denied'
    if any(m in text for m in CLOSED_MARKERS):
        return 'closed'
    if status >= 400:
        return 'client-error'
    return 'ok'


def verdict(row, role, outcome, js_errors, asset_errors):
    expected = [r.strip() for r in row.get('expected_roles', '').split(',') if r.strip()]
    endpoint = row.get('kind') == 'endpoint'
    if outcome in ('load-failed', 'server-error'):
        return 'endpoint-error' if endpoint else 'server-error'
    # Endpoints reject a GET without their parameters
    if endpoint and outcome == 'client-error':
        return 'info'
    if expected and role not in expected and outcome in ('ok', 'download'):
        return 'unexpected-allow'
    if expected and role in expected:
        if outcome == 'not-found':
            return 'not-found'
        if outcome in ('denied', 'login-required', 'client-error'):
            return 'unexpected-deny'
    if outcome in ('ok', 'download', 'closed'):
        if js_errors:
            return 'js-error'
        if asset_errors:
            return 'asset-error'
    if outcome == 'closed':
        return 'closed'
    return 'ok' if expected else 'info'


def slug(url):
    base = re.sub(r'[^A-Za-z0-9]+', '_', url).strip('_')[:80] or 'root'
    return f'{base}_{hashlib.sha1(url.encode()).hexdigest()[:8]}'


async def visit(context, base_url, row, role, args):
    from playwright.async_api import Error as PlaywrightError
    url = row['url']
    page = await context.new_page()
    js_errors, asset_errors, blocked = [], [], []
    page.on('console', lambda m: js_errors.append(m.text[:300]) if m.type == 'error' else None)
    page.on('pageerror', lambda e: js_errors.append(f'uncaught: {str(e)[:300]}'))

    def on_response(resp):
        if resp.status >= 400 and resp.request.resource_type in ('script', 'stylesheet', 'image', 'font'):
            asset_errors.append(f'{resp.status} {resp.url}')

    def on_failed(req):
        if req.url in blocked:
            return
        if req.resource_type in ('script', 'stylesheet', 'image', 'font'):
            asset_errors.append(f'failed {req.url} ({req.failure})')
    page.on('response', on_response)
    page.on('requestfailed', on_failed)

    async def guard(route):
        if route.request.method in ('GET', 'HEAD', 'OPTIONS') or args.allow_post:
            await route.continue_()
        else:
            blocked.append(route.request.url)
            await route.abort()
    await page.route('**/*', guard)

    result = {'url': url, 'role': role, 'status': '', 'final_url': '', 'title': '', 'screenshot': ''}
    text = ''
    try:
        response = await page.goto(base_url + url, wait_until='load', timeout=args.timeout * 1000)
        if args.settle_ms:
            await page.wait_for_timeout(args.settle_ms)
        status = response.status if response else None
        final = urlparse(page.url)
        result.update(status=status, final_url=final.path + (f'?{final.query}' if final.query else ''),
                      title=(await page.title())[:200])
        text = await page.evaluate("document.body ? document.body.innerText : ''")
        outcome = classify(status, urlparse(url).path, final.path, text)
        if args.screenshots != 'none':
            name = os.path.join('screenshots', role, slug(url) + '.jpg')
            try:
                await page.screenshot(path=os.path.join(args.out, name), type='jpeg', quality=60,
                                      full_page=args.screenshots == 'full')
                result['screenshot'] = name
            except PlaywrightError:
                pass
    except PlaywrightError as e:
        message = str(e)
        if 'Download is starting' in message or 'net::ERR_ABORTED' in message:
            outcome = 'download'
        else:
            outcome = 'load-failed'
            js_errors.append(f'navigation: {message.splitlines()[0][:300]}')
    finally:
        await page.close()

    result.update(
        outcome=outcome,
        verdict=verdict(row, role, outcome, js_errors, asset_errors),
        expected_roles=row.get('expected_roles', ''),
        js_errors=' | '.join(dict.fromkeys(js_errors)),
        asset_errors=' | '.join(dict.fromkeys(asset_errors)),
        blocked_requests=' | '.join(dict.fromkeys(blocked)),
        text_length=len(text),
        **{k: row.get(k, '') for k in ('kind', 'area', 'module', 'view', 'skip_reason', 'source')},
    )
    return result


async def session_alive(context, base_url):
    page = await context.new_page()
    try:
        await page.goto(base_url + SESSION_CANARY, wait_until='load')
        return not urlparse(page.url).path.startswith(LOGIN_PATHS)
    finally:
        await page.close()


async def crawl(rows, sessions, args):
    # Imported here so the rest of this file works without Playwright installed
    from playwright.async_api import async_playwright
    base_url = args.base_url.rstrip('/')
    results, warnings = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=args.chromium or None)
        contexts = {}
        for role in args.roles:
            context = await browser.new_context(accept_downloads=False, ignore_https_errors=args.ignore_https_errors,
                                                viewport={'width': 1280, 'height': 900})
            if role != 'anonymous':
                info = sessions['roles'][role]
                await context.add_cookies([{'name': sessions['cookie_name'], 'value': info['session_key'],
                                            'url': base_url}])
            contexts[role] = context

        for role in args.roles:
            if role != 'anonymous' and not await session_alive(contexts[role], base_url):
                warnings.append(f'{role}: session is not logged in before the crawl; '
                                'recreate sessions.json')

        jobs = [(row, role) for row in rows for role in args.roles]
        semaphore = asyncio.Semaphore(args.concurrency)
        done = 0

        async def run(row, role):
            nonlocal done
            async with semaphore:
                result = await visit(contexts[role], base_url, row, role, args)
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f'{done}/{len(jobs)} pages', flush=True)
            return result
        results = await asyncio.gather(*(run(row, role) for row, role in jobs))

        for role in args.roles:
            if role != 'anonymous' and not await session_alive(contexts[role], base_url):
                warnings.append(f'{role}: session was logged out during the crawl; '
                                'its later results may show spurious login redirects')
        await browser.close()
    return list(results), warnings


def load_results(path):
    with open(path, encoding='utf-8') as f:
        return {(r['url'], r['role']): r for r in json.load(f)['results']}


def compare(results, previous):
    """Rows whose outcome, status or verdict differs from an earlier run."""
    changes = []
    for r in results:
        old = previous.get((r['url'], r['role']))
        if old is None:
            changes.append({'url': r['url'], 'role': r['role'], 'change': 'new page',
                            'before': '', 'after': f"{r['outcome']} ({r['status']})"})
            continue
        for key in ('outcome', 'status', 'verdict'):
            if str(old.get(key)) != str(r.get(key)):
                changes.append({'url': r['url'], 'role': r['role'], 'change': key,
                                'before': str(old.get(key)), 'after': str(r.get(key))})
    seen = {(r['url'], r['role']) for r in results}
    for key, old in previous.items():
        if key not in seen:
            changes.append({'url': key[0], 'role': key[1], 'change': 'page gone',
                            'before': f"{old['outcome']} ({old['status']})", 'after': ''})
    return changes


def write_report(results, warnings, changes, skipped, args):
    by_verdict = Counter((r['verdict'], r['role']) for r in results)
    e = html.escape

    def cell(r, key):
        value = str(r.get(key, ''))
        if key == 'url':
            return f'<a href="{e(args.base_url.rstrip("/") + value)}">{e(value)}</a>'
        if key == 'screenshot' and value:
            return f'<a href="{e(value)}">view</a>'
        return e(value[:400])

    cols = ['verdict', 'url', 'role', 'outcome', 'status', 'final_url', 'expected_roles',
            'js_errors', 'asset_errors', 'screenshot', 'module', 'skip_reason']
    order = {v: i for i, v in enumerate(VERDICTS)}
    rows_html = ''.join(
        f'<tr class="v-{e(r["verdict"])}">' + ''.join(f'<td>{cell(r, c)}</td>' for c in cols) + '</tr>'
        for r in sorted(results, key=lambda r: (order[r['verdict']], r['url'], ROLES.index(r['role']))))
    summary = ''.join(
        f'<tr><td><label><input type="checkbox" data-v="{v}" {"checked" if v not in ("ok", "info") else ""}> '
        f'{v}</label></td><td>{e(VERDICT_HELP[v])}</td>'
        + ''.join(f'<td>{by_verdict.get((v, role), 0) or ""}</td>' for role in args.roles) + '</tr>'
        for v in VERDICTS)
    change_html = ''.join(
        f'<tr><td>{e(c["url"])}</td><td>{e(c["role"])}</td><td>{e(c["change"])}</td>'
        f'<td>{e(c["before"])}</td><td>{e(c["after"])}</td></tr>' for c in changes)
    warn_html = ''.join(f'<li>{e(w)}</li>' for w in warnings)

    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crawl report</title>
<style>
body {{ font: 14px system-ui, sans-serif; margin: 16px; background: #fff; color: #111; }}
table {{ border-collapse: collapse; margin-bottom: 24px; }}
td, th {{ border: 1px solid #ccc; padding: 3px 6px; vertical-align: top; text-align: left; }}
#results td {{ max-width: 360px; overflow-wrap: anywhere; }}
.v-server-error td:first-child, .v-unexpected-allow td:first-child {{ background: #f8d0d0; }}
.v-not-found td:first-child, .v-unexpected-deny td:first-child {{ background: #fbe6c2; }}
.v-js-error td:first-child, .v-asset-error td:first-child {{ background: #fff6bf; }}
.warn {{ color: #a40000; }}
</style></head><body>
<h1>Crawl report</h1>
<p>{e(args.base_url)} &middot; {len(results)} page visits &middot; {skipped} inventory rows not crawlable
(see inventory.csv skip_reason) &middot; inventory: {e(args.inventory)}</p>
{f'<ul class="warn">{warn_html}</ul>' if warnings else ''}
<h2>Summary</h2>
<p>Tick a verdict to show its rows below.</p>
<table><tr><th>verdict</th><th>meaning</th>{''.join(f'<th>{e(r)}</th>' for r in args.roles)}</tr>{summary}</table>
{f'<h2>Changes since {e(args.compare)} ({len(changes)})</h2><table><tr><th>url</th><th>role</th><th>change</th><th>before</th><th>after</th></tr>{change_html}</table>' if args.compare else ''}
<h2>Results</h2>
<table id="results"><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr>{rows_html}</table>
<script>
function apply() {{
  const on = new Set([...document.querySelectorAll('input[data-v]')].filter(i => i.checked).map(i => i.dataset.v));
  document.querySelectorAll('#results tr[class]').forEach(tr => {{
    tr.style.display = on.has(tr.className.slice(2)) ? '' : 'none';
  }});
}}
document.querySelectorAll('input[data-v]').forEach(i => i.addEventListener('change', apply));
apply();
</script>
</body></html>"""
    with open(os.path.join(args.out, 'report.html'), 'w', encoding='utf-8') as f:
        f.write(page)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--inventory', required=True, help='inventory.json from manage.py url_inventory')
    parser.add_argument('--sessions', help='sessions.json from manage.py crawl_sessions (omit to crawl anonymously)')
    parser.add_argument('--base-url', required=True, help='e.g. http://localhost:8000')
    parser.add_argument('--out', default='crawl-results', help='output directory')
    parser.add_argument('--roles', help='comma-separated roles (default: anonymous plus every role in --sessions)')
    parser.add_argument('--area', action='append', default=[],
                        help='only crawl inventory rows in this area, e.g. learn or admin (repeatable)')
    parser.add_argument('--url-regex', help='only crawl URLs matching this regular expression')
    parser.add_argument('--limit', type=int, help='crawl at most this many inventory rows')
    parser.add_argument('--concurrency', type=int, default=4, help='pages loaded at once (default 4)')
    parser.add_argument('--timeout', type=int, default=60, help='seconds to wait for a page (default 60)')
    parser.add_argument('--settle-ms', type=int, default=300,
                        help='wait after load to catch late JavaScript errors (default 300)')
    parser.add_argument('--screenshots', choices=['none', 'viewport', 'full'], default='viewport')
    parser.add_argument('--compare', metavar='RESULTS_JSON', help='results.json from an earlier crawl to diff against')
    parser.add_argument('--allow-post', action='store_true',
                        help='let pages send non-GET requests (blocked by default)')
    parser.add_argument('--chromium', default=os.environ.get('CRAWL_CHROMIUM'),
                        help='path to a Chromium binary (default: the one Playwright installed)')
    parser.add_argument('--ignore-https-errors', action='store_true', help='accept self-signed certificates')
    parser.add_argument('--target-is-disposable', action='store_true',
                        help='required for a non-local --base-url: confirms the site is a throwaway copy')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    host = urlparse(args.base_url).hostname
    if host not in LOCAL_HOSTS and not args.target_is_disposable:
        sys.exit(f'{host} is not a local address. Only crawl a disposable copy of a site; '
                 'pass --target-is-disposable to confirm this is one.')

    with open(args.inventory, encoding='utf-8') as f:
        inventory = json.load(f)
    sessions = {'roles': {}}
    if args.sessions:
        with open(args.sessions, encoding='utf-8') as f:
            sessions = json.load(f)
    args.roles = ([r.strip() for r in args.roles.split(',') if r.strip()] if args.roles
                  else ['anonymous'] + [r for r in ROLES if r in sessions['roles']])
    missing = [r for r in args.roles if r != 'anonymous' and r not in sessions['roles']]
    if missing:
        sys.exit(f'No session for role(s) {", ".join(missing)}; run manage.py crawl_sessions')

    all_rows = inventory['rows']
    rows = [r for r in all_rows if r['crawlable'] == 'yes' and r['url']]
    if args.area:
        rows = [r for r in rows if r['area'] in args.area]
    if args.url_regex:
        rows = [r for r in rows if re.search(args.url_regex, r['url'])]
    if args.limit:
        rows = rows[:args.limit]

    for role in args.roles:
        os.makedirs(os.path.join(args.out, 'screenshots', role), exist_ok=True)
    print(f'Crawling {len(rows)} URLs as {", ".join(args.roles)}', flush=True)
    results, warnings = asyncio.run(crawl(rows, sessions, args))
    changes = compare(results, load_results(args.compare)) if args.compare else []

    with open(os.path.join(args.out, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump({'base_url': args.base_url, 'inventory': args.inventory, 'roles': args.roles,
                   'warnings': warnings, 'results': results}, f, indent=1)
    with open(os.path.join(args.out, 'results.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    if args.compare:
        with open(os.path.join(args.out, 'changes.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['url', 'role', 'change', 'before', 'after'])
            writer.writeheader()
            writer.writerows(changes)
    write_report(results, warnings, changes, len(all_rows) - len(rows), args)

    counts = Counter(r['verdict'] for r in results)
    print(', '.join(f'{v}: {counts[v]}' for v in VERDICTS if counts[v]))
    for w in warnings:
        print('WARNING:', w)
    print(f'Report: {os.path.join(args.out, "report.html")}')
    # Non-zero exit when anything needs attention, for use in CI
    return 1 if counts['server-error'] or counts['unexpected-allow'] else 0


if __name__ == '__main__':
    sys.exit(main())
