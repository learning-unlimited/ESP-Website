""" The middleware to implement the queue. """

import time
from esp.queue.models import *
from django.http import HttpResponse

class QueueMiddleware(object):

    def process_request(self, request):
        q = QueueItem(request)

        try:
            q.update_queue()
        except WaitInQueue, wait:
            pass
        else:
            return None


        message = """
<h1>Please wait...</h1>

<p>Our server is under extreme load. To satisfy everyone's need, you
have been placed in a queue. You are #%s in a line of %s people.
<br /><br />
<!-- Your estimated time is: <strong>TODO</strong> //-->

<strong>Note: Please do not refresh and/or close this page! This
page will automatically reload and update for you.</strong>
""" % (wait.num_in_queue, wait.queue_size)

        page = open(QUEUE_FILE, 'r').read(50000) % message

        response = HttpResponse(page)
        response['Refresh'] = str(wait.refresh_time)

        return response
