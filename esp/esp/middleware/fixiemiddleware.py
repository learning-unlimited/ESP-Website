from django.utils.deprecation import MiddlewareMixin


class FixIEMiddleware(MiddlewareMixin):
    """
    Quick MiddleWare that will fix the bug reported at
    http://support.microsoft.com/kb/824847/en-us?spid=8722&sid=global (thanks aconbere)
    for Internet Explorer since Microsoft doesn't know how to do HTTP.

    To use: Make sure you put this at the *beginning* of your middleware
    list (since Django applies responses in reverse order).
    """

    def process_response(self, request, response):

        safe_mime_types = (
            "text/html",
            "text/plain",
            "text/sgml",
        )

        try:
            user_agent = request.META.get("User-Agent", "")
            if "MSIE" not in user_agent.upper():
                return response
        except (KeyError, AttributeError):
            return response

        content_type = getattr(response, "content_type", "")
        if content_type.lower() not in safe_mime_types:
            try:
                del response["Vary"]
                response["Pragma"] = "no-cache"
                response["Cache-Control"] = "no-cache, must-revalidate"
            except KeyError:
                return response

        return response

