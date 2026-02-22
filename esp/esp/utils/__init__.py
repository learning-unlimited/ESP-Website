"""
This app contains the little things that didn't really belong anywhere else.

The modules in this directory are globally relevant
    but too small to merit their own apps.

The functions in this file are globally relevant, too annoying to inline,
    and too small to merit their own modules.
"""

import sys
from urllib.parse import quote_plus

def force_str(x):
    """
    Forces x to a str, encoding via utf8 if needed.

    >>> force_str('\\xc3\\x85ngstrom')
    '\\xc3\\x85ngstrom'
    >>> force_str(u'\\xc5ngstrom')
    '\\xc3\\x85ngstrom'

    """
    if isinstance(x, str) or isinstance(x, str):
        return x
    return str(x).encode('utf8')

def ascii(x):
    """
    Forces x to urlencoded ascii; spaces are replaced with + signs.

    This is NOT the identity on str objects;
    since str objects carry no indication of whether they've been quoted,
    double quoting WILL occur if you apply this more than once.

    >>> ascii('\\xc3\\x85ngstrom')
    '%C3%85ngstrom'
    >>> ascii(u'\\xc5ngstrom')
    '%C3%85ngstrom'

    """
    return quote_plus(force_str(x))

# copied from: https://portingguide.readthedocs.io/en/latest/comparisons.html
def cmp(x, y):
    """
    Replacement for built-in function cmp that was removed in Python 3

    Compare the two objects x and y and return an integer according to
    the outcome. The return value is negative if x < y, zero if x == y
    and strictly positive if x > y.
    """

    return (x > y) - (x < y)
