__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.qsdmedia.models import Media
from esp.tests.util import CacheFlushTestCase as TestCase

from django.core.files.uploadhandler import MemoryFileUploadHandler, StopFutureHandlers

class QSDMediaTest(TestCase):
    def test_upload(self):
        #   Pretend to upload a file
        file_data = "here is some test data"
        file_size = len(file_data)
        handler = MemoryFileUploadHandler()
        handler.handle_raw_input(file_data, None, file_size, None)
        try:
            handler.new_file('test', 'test_file.txt', 'text/plain', file_size)
        except StopFutureHandlers:
            pass
        file = handler.file_complete(file_size)
        media = Media(friendly_name = 'Test QSD Media')
        media.handle_file(file, file.name)
        media.save()

        #   Check that the file can be downloaded from the proper link
        url = '/download/%s' % media.hashed_name
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        #   Delete the QSD Media object
        media.delete()

        #   Check that the file can no longer be downloaded
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
