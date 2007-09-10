""" Models for the Queue. """
from django.conf import settings
from esp.utils.memdb import mem_db
import md5, time

try:
    import cPickle as pickle
except ImportError:
    import pickle

QUEUE_FILE = settings.TEMPLATE_DIRS[0] + '/errors/queue.html'

__all__ = ['QUEUE_FILE','QueueItem','WaitInQueue']

##########
# DEFAULTS
# Note: These are adjustable in the memory database.
##########
DEFAULT_TIMEOUT = 600#: Ten minute timeout.
MAX_SIZE = 120
REFRESH_TIME = 30

class WaitInQueue(Exception):
    """ The user is waiting in a queue. """
    def __init__(self, num_in_queue=0, queue_size=0, expected_time=0, refresh_time=0):
        self.num_in_queue = num_in_queue
        self.expected_time = expected_time
        self.queue_size = queue_size
        self.refresh_time = refresh_time

class QueueProperty(object):
    def __init__(self, name, default=None):
        self.name = name
        self.default = default

    def __set__(self, instance, value):
        if not hasattr(instance, '_properties'):
            instance._properties = {}
        instance._properties[self.name] = value
        mem_db.set(self.name, pickle.dumps(value))

    def __get__(self, instance, class_):
        if not hasattr(instance, '_properties'):
            instance._properties = {}

        if self.name not in instance._properties:
            value = mem_db.get(self.name) or self.default
            try:
                value = pickle.loads(value)
            except:
                pass

            instance._properties[self.name] = value

        return instance._properties[self.name]


class QueueItem(object):
    max_inside = QueueProperty('QUEUE_MAX', MAX_SIZE)#: The number of people inside
    timeout = QueueProperty('QUEUE_TIMEOUT', DEFAULT_TIMEOUT)#: How long before the person times out
    inside_keys = QueueProperty('QUEUE_KEYS', [])#: Keys inside the web site
    queue_keys = QueueProperty('QUEUE_LIST', [])#: Keys waiting on the doorstep
    refresh_time = QueueProperty('QUEUE_REFRESH_TIME', REFRESH_TIME)#: How long to refresh

    def __init__(self, request=None):
        if request is not None:
            self.ip_addr = request.META['REMOTE_ADDR']
            self.user_agent = request.META.get('HTTP_USER_AGENT','')
            self.request = request
            self.cache_key = 'QUEUE__' + md5.new(self.ip_addr + '::' + self.user_agent).hexdigest()
            # If the user signs out, remove them
            if 'signout' in request.path:
                mem_db.delete(self.cache_key)

    def clean_keys(self):
        inside_old_keys = self.inside_keys
        queue_old_keys = self.queue_keys
        queue_new_keys, inside_new_keys = [],[]

        for key in inside_old_keys:
            last_time = mem_db.get(key)
            if last_time is not None:
                inside_new_keys.append(key)

        for key in queue_old_keys:
            last_time = QueueItem.get_time_from_value(mem_db.get(key))
            if key != self.cache_key or \
               abs(time.time() - last_time - self.refresh_time) < (.2 * self.refresh_time):
                # A reload has to be within 20% of when it was supposed to be refreshed.
                queue_new_keys.append(key)

        if set(inside_new_keys) != set(inside_old_keys):
            self.inside_keys = inside_new_keys

        if set(queue_new_keys) != set(queue_old_keys):
            self.queue_keys = queue_new_keys

    @staticmethod
    def get_time_from_value(value):
        if value is None:
            return 0
        try:
            return float(value.split(',', 1)[0])
        except:
            return 0

    @property
    def cache_value(self):
        return ','.join((str(time.time()), self.ip_addr, self.user_agent))

    def update_queue(self):
        self.clean_keys()

        if self.cache_key not in self.inside_keys:
            if self.cache_key not in self.queue_keys:
                # We are currently not in the queue.
                queue_keys = self.queue_keys
                queue_keys.append(self.cache_key)
                self.queue_keys = queue_keys
            num_avail = self.max_inside - len(self.inside_keys)

            if self.cache_key in self.queue_keys[:num_avail]:
                queue_keys = self.queue_keys
                queue_keys.remove(self.cache_key)
                
                inside_keys = self.inside_keys
                inside_keys.append(self.cache_key)

                self.queue_keys = queue_keys
                self.inside_keys = inside_keys
            else:
                mem_db.set(self.cache_key, self.cache_value, self.timeout)
                raise WaitInQueue(self.queue_keys.index(self.cache_key) + 1,
                                 len(self.queue_keys),
                                 0,
                                 self.refresh_time)

        print """=============
%s
==========
%s
==========""" % (self.queue_keys, self.inside_keys)
        mem_db.set(self.cache_key, self.cache_value, self.timeout)

        return True
