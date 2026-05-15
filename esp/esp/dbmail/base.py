

class BaseHandler(object):

    send = False
    preserve_headers = False

    def __init__(self, handler, message):
        self.handler = handler
        self.message = message

    def process(self, *args, **kwargs):
        raise NotImplementedError
