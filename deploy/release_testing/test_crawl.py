"""Tests for crawl.py's result handling. Run with: python -m pytest deploy/release_testing"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from crawl import classify, compare, load_progress, main, slug, verdict  # noqa: E402

PAGE = {'expected_roles': 'teacher, admin', 'kind': 'page'}


def test_classify():
    assert classify(None, '/a', '/a', '') == 'load-failed'
    assert classify(500, '/a', '/a', '') == 'server-error'
    assert classify(404, '/a', '/a', '') == 'not-found'
    assert classify(200, '/teach/x', '/myesp/login/', '') == 'login-required'
    assert classify(200, '/admin/', '/admin/login/', '') == 'login-required'
    assert classify(200, '/a', '/a', 'Sorry Bob, you are not an administrator of this program.') == 'denied'
    assert classify(200, '/a', '/a', 'This page is not currently open, possibly because you are '
                                     'either too early or too late') == 'closed'
    assert classify(200, '/a', '/a', 'It appears you are logged in. This page is not useful for you.') == 'denied'
    assert classify(500, '/a', '/a', 'Your request could not be processed. Please check what you '
                                     'submitted and try again.') == 'user-error'
    assert classify(400, '/a', '/a', '') == 'client-error'
    assert classify(200, '/a', '/a', 'Welcome') == 'ok'


def test_verdict():
    assert verdict(PAGE, 'teacher', 'ok', [], []) == 'ok'
    assert verdict(PAGE, 'student', 'ok', [], []) == 'unexpected-allow'
    assert verdict(PAGE, 'student', 'denied', [], []) == 'ok'
    assert verdict(PAGE, 'teacher', 'denied', [], []) == 'unexpected-deny'
    assert verdict(PAGE, 'teacher', 'server-error', [], []) == 'server-error'
    assert verdict(PAGE, 'teacher', 'user-error', [], []) == 'needs-input'
    assert verdict(PAGE, 'teacher', 'client-error', [], []) == 'needs-input'
    assert verdict(PAGE, 'teacher', 'ok', ['TypeError'], []) == 'js-error'
    assert verdict(PAGE, 'teacher', 'ok', [], ['404 /x.css']) == 'asset-error'
    assert verdict({'expected_roles': '', 'kind': 'page'}, 'teacher', 'ok', [], []) == 'info'


def test_endpoint_verdicts():
    endpoint = dict(PAGE, kind='endpoint')
    assert verdict(endpoint, 'teacher', 'server-error', [], []) == 'endpoint-error'
    assert verdict(endpoint, 'teacher', 'client-error', [], []) == 'needs-input'


def test_compare():
    old = {('/a', 'admin'): {'url': '/a', 'role': 'admin', 'outcome': 'ok', 'status': 200, 'verdict': 'ok'},
           ('/gone', 'admin'): {'url': '/gone', 'role': 'admin', 'outcome': 'ok', 'status': 200, 'verdict': 'ok'}}
    new = [{'url': '/a', 'role': 'admin', 'outcome': 'server-error', 'status': 500, 'verdict': 'server-error'},
           {'url': '/b', 'role': 'admin', 'outcome': 'ok', 'status': 200, 'verdict': 'ok'}]
    changes = {(c['url'], c['change']) for c in compare(new, old)}
    assert changes == {('/a', 'outcome'), ('/a', 'status'), ('/a', 'verdict'),
                       ('/b', 'new page'), ('/gone', 'page gone')}


def test_load_progress_skips_a_half_written_line(tmp_path):
    path = tmp_path / 'progress.jsonl'
    path.write_text('{"url": "/a", "role": "admin"}\n{"url": "/b", "ro')
    assert load_progress(str(path)) == [{'url': '/a', 'role': 'admin'}]
    assert load_progress(str(tmp_path / 'missing.jsonl')) == []


def test_slug_is_unique_per_url():
    assert slug('/learn/a?b') != slug('/learn/a_b')


def test_refuses_remote_sites_without_confirmation(tmp_path):
    try:
        main(['--inventory', str(tmp_path / 'x.json'), '--base-url', 'https://example.org'])
    except SystemExit as e:
        assert 'not a local address' in str(e)
    else:
        raise AssertionError('expected SystemExit')
