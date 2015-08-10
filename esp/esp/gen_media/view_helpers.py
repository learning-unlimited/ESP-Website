
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

import weasyprint 

from django.template import RequestContext
from django.template.loader import get_template
from django.http import HttpResponse


class PDFResponseMixin(object):

    filename = None#set this attribute to customize the filename

    def get_pdf_response(self, context, **response_kwargs):
        """
        Sets content type to application/pdf. Converts the default response into a pdf 
        document. Assumes that inheriting class defines a template_name
        """
        if not hasattr(self, 'template_name'):
            raise ValueError('A template_name was not defined')

        filename = self.filename or self.template_name
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="%s.pdf"'%filename
        template = get_template(self.template_name)
        html = template.render(RequestContext(self.request, context))

        weasyprint.HTML(string=html).write_pdf(response)

        return response
