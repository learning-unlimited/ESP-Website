

class BaseHandler(object):

    send = False

    def __init__(self, handler, message):
        self.handler = handler
        self.message = message

    def process(self, *args, **kwargs):
        raise NotImplementedError
