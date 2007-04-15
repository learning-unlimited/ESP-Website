"""
Tightens up response content by removed superflous line breaks and whitespace.
By Doug Van Horn
"""

class StripWhitespaceMiddleware:
    """
    Strips leading and trailing whitespace from response content.
    """
    def process_response(self, request, response):
        if("text" in response['Content-Type'] ):
            new_content = response.content.strip()
            response.content = new_content
            return response
        else:
            return response
