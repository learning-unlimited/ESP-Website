"""
This app contains the little things that didn't really belong anywhere else.

The modules in this directory are globally relevant
    but too small to merit their own apps.

The functions in this file are globally relevant, too annoying to inline,
    and too small to merit their own modules.
"""

import sys
from urllib import quote_plus

def echo( *args, **kwargs ):
    """
    echo( *args, quiet=False )
    
    A print function that attempts to discard encoding errors.
    Unrepresentable characters become question marks.
    Raw bytestrings (str) get escaped.

    Pass quiet=True to make it nop.

    >>> echo( 123 )
    123
    >>> echo( u'One \xc3\x85ngstrom' ) #doctest: +ELLIPSIS
    One ...ngstrom
    >>> echo( 'One \xc3\x85ngstrom' ) #doctest: +ELLIPSIS
    One ...ngstrom
    >>> echo( echo ) #doctest: +ELLIPSIS
    <function echo at ...>
    """
    if kwargs.has_key('quiet') and kwargs['quiet']:
        return
    for x in args:
        encoding = 'ascii'
        if hasattr( sys.stdout, 'encoding' ):
            encoding = sys.stdout.encoding
        if isinstance(x, str):
            x = x.encode('string_escape')
        print unicode(x).encode( encoding, 'replace' )

def force_str(x):
    """
    Forces x to a str, encoding via utf8 if needed.

    >>> force_str('\\xc3\\x85ngstrom')
    '\\xc3\\x85ngstrom'
    >>> force_str(u'\\xc5ngstrom')
    '\\xc3\\x85ngstrom'

    """
    if isinstance(x, str):
        return x
    return unicode(x).encode('utf8')

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
