""" Base class for generated media. """
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

from django.conf import settings

import hashlib
import os

__all__ = ['GenMediaBase']

class GenMediaBase(object):
    """ Generated content with free caching. """

    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'EXT'):
            raise Exception("ERROR: subclass must provide EXT for file extension.")
        if not hasattr(self, 'DIR'):
            raise Exception("ERROR: subclass must provide DIR for output directory.")

        self.file_base = hashlib.sha1(self._key()).hexdigest()
        self.file_name = self.file_base + '.' + self.EXT

        # Avoid having too many files in a single directory
        # (git does this too. :D And mediawiki does something similar.)
        self.cache_dir = self.file_name[:2]
        self.file_name = self.file_name[2:]
        self.file_path = os.path.join(self.DIR, self.cache_dir, self.file_name)

        if not os.path.exists(self.file_path):
            # Make directory if it doesn't exist
            save_dir = os.path.dirname(self.local_path)
            if not os.path.exists(save_dir):
                os.mkdir(save_dir)
            # Generate the file
            self._generate_file()
    
    def _key(self):
        """ A unique identifier based on the arguments. """
        raise NotImplementedError("Subclass must implement _key.")

    @property
    def local_path(self):
        """ The path to the file on the filesystem. """
        return os.path.join(settings.MEDIA_ROOT, self.file_path)

    @property
    def url(self):
        """ The URL of the file. """
        if settings.MEDIA_URL.endswith('/'):
            return settings.MEDIA_URL + self.DIR + '/' \
                    + self.cache_dir + '/' + self.file_name
        else:
            return settings.MEDIA_URL + '/' + self.DIR + '/' \
                    + self.cache_dir + '/' + self.file_name

    def _generate_file(self):
        """ Generates the file. """
        raise NotImplementedError("Subclass must implement _generate_file.")
    @property
    def img(self):
        """ An image tag, ready to be inserted into HTML. """
        from django.utils.html import escape
        return '<img src="%s" alt="%s" title="%s" border="0" class="LaTeX" align="middle" />' \
                % (self.url, escape(self.content), escape(self.content))

