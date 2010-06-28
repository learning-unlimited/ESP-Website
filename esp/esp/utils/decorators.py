
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

class OptionalDecorator(object):
    """ A simple decorator to turn a function into a no-op.  If the argument evaluates
        to true, it's transparent.  Otherwise it generates a decorator that causes
        the function to always return False. """
    
    def __init__(self, value, *args, **kwargs):
        self.value = value

    def __call__(self, func, *args, **kwargs):
    
        def _do_nothing(*args, **kwargs):
            return False
    
        if hasattr(self, 'value'):
            if self.value:
                return func
            else:
                return _do_nothing
        elif value:
            return func
        else:
            return _do_nothing

enable_with_setting = OptionalDecorator
