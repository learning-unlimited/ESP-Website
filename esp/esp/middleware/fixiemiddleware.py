try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

class FixIEMiddleware(MiddlewareMixin):
    """
    Quick MiddleWare that will fix the bug reported at
    http://support.microsoft.com/kb/824847/en-us?spid=8722&sid=global (thanks aconbere)
    for Internet Explorer since Microsoft doesn't know how to do HTTP.

    To use: Make sure you put this at the *beginning* of your middleware
    list (since Django applies responses in reverse order).
    """

    def process_response(self, request, response):

        # a list of mime-types that are decreed "Vary-safe" for IE
        safe_mime_types = ('text/html',
                           'text/plain',
                           'text/sgml',
                           )

        # establish that the user is using IE
        try:
            if 'MSIE' not in request.META['User-Agent'].upper():
                return response
        except KeyError:
            return response


        # IE will break
        if response.mimetype.lower() not in safe_mime_types:
            try:
                del response['Vary']
                response['Pragma'] = 'no-cache'
                response['Cache-Control'] = 'no-cache, must-revalidate'
            except KeyError:
                return response

        return response

