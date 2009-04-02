""" The stupidest middleware ever.

It's sole purpose is to detect whether the server has been started."""

class ServerLoadedMiddleware(object):
    server_loaded = False
    def process_request(self, request):
        ServerLoadedMiddleware.server_loaded = True
