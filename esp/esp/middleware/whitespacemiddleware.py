"""
Tightens up response content by removed superflous line breaks and whitespace.
By Doug Van Horn
"""

class StripWhitespaceMiddleware:
    """
    Strips leading and trailing whitespace from response content.
    """
    def process_response(self, request, response):
        # If we have a HttpResponseNotModified, for instance, there might not
        # be a content-type field.  Handle that gracefully.
        content_type = response.get('Content-Type')
        if content_type is not None and "text" in content_type:
            new_content = response.content.strip()
            response.content = new_content
            response['Content-Length'] = str(len(response.content))
            return response
        else:
            return response
