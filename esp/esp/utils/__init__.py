"""
This app contains the little things that didn't really belong anywhere else.

The modules in this directory are globally relevant
    but too small to merit their own apps.

The functions in this file are globally relevant, too annoying to inline,
    and too small to merit their own modules.
"""

import sys

def echo( *args, **kwargs ):
    """
    echo( *args, quiet=False )
    
    A print function that attempts to discard encoding errors.
    Unrecognized characters become question marks.
    Pass quiet=True to make it nop.
    
    >>> echo( 123 )
    123
    >>> echo( u'\xc3\x85ngstrom' )
    ... ngstrom
    >>> echo( '\xc3\x85ngstrom' )
    Traceback (most recent call last):
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 0: ordinal not in range(128)
    >>> echo( echo )
    <function echo at ... >
    """
    if kwargs.has_key('quiet') and kwargs['quiet']:
        return
    for x in args:
        encoding = 'ascii'
        if hasattr( sys.stdout, 'encoding' ):
            encoding = sys.stdout.encoding
        print unicode(x).encode( encoding, 'replace' )
