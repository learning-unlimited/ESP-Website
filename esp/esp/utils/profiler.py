import sys
from datetime import datetime, timedelta

# Modules to omit. Mostly built-in and uninteresting.
excluded_modules = set(['site', 'encodings', 'profiler', 'codecs', 'posixpath', 'abc',
                        'genericpath', 'warnings', '_abcoll', 'copy_reg', 
                        'sitecustomize', 'apport_python_hook', 'stat', 'os', 'linecache',
                        'UserDict', 'apport', 'xml', 'subprocess', 'tempfile', 'random',
                        'quopri', 'tempfile', 'problem_report', 'email', 
                        'apt', '__future__', 'psycopg2', 'iprof' ])

def empty():
    pass

# Iterate over all 
class Profiler(object):

    def __init__(self):
        self.enabled = False
        self.overhead_dt = timedelta()
        self.overhead_ncalls = 1

        # Objects with profiler installed: id  -> obj
        self.installed = {}

        # Changelog: [ [obj, key, oldv, newv], ... ]
        self.changelog = []

        # Inner time adjustment
        self.inner = timedelta()
        self.icalls = 0

        # Profiling Data: function id -> data
        # data format: [ function, path, ncalls, total_time, inner_time ]
        self.data = {}
        return

    # Clear the profiler timing values to 0
    def clear(self):
        for k in self.data:
            entry = self.data[k]
            entry[2] = 0
            entry[3] = 0
            entry[4] = timedelta()
            entry[5] = timedelta()
        return

    def set_overhead(self):
        empty_wrapped = self.install_obj('profiler', empty)
        for i in xrange(0,100000):
            empty_wrapped()
        entry = self.data[id(empty)]
        self.overhead_dt = entry[4]
        self.overhead_ncalls = entry[2]
        print "Overhead set at %s per %d" % (str(self.overhead_dt),self.overhead_ncalls)


    def install(self):
        modlist = dict(sys.modules)
        for k in modlist:
            self.install_obj('', modlist[k])
        self.enabled = True
        self.set_overhead()

        return None

    def uninstall(self):
        self.enabled = False
        fullcount = len(self.changelog)
        count = 0
        for obj, k, oldv, newv in self.changelog:
            if k in obj.__dict__ and id(obj.__dict__[k]) == id(newv):
                oldv.__dict__ = newv.__dict__
                setattr(obj, k, oldv)
                count += 1
            else:
                print "Couldn't remove: %s, '%s', %d, %d" % (str(obj), k, id(oldv), id(newv))


        return (count, fullcount)

    # Install the profiler in "obj" and all subobjects/submodules.
    # Returns the new object if it needs to be replaced.
    # Otherwise, returns None.
    def install_obj(self, prefix, obj):
        global excluded_modules

        # Check to see if the object is already installed
        if obj is None or id(obj) in self.installed:
            return None

        self.installed[id(obj)] = obj

        typename = type(obj).__name__
        if typename == 'str' or typename == 'int':
            return None

        if typename == 'module':
            # Skip built-in modules
            if not hasattr(obj, '__file__'):
                return None

            # Skip excluded modules
            nameset = set(obj.__name__.split("."))
            if len(nameset & excluded_modules) > 0:
                return None

            for k in obj.__dict__:
                oldv = obj.__dict__[k]
                newv = self.install_obj('', oldv)
                if newv:
                    setattr(obj, k, newv)
                    self.changelog.append([obj, k, oldv, newv])

        if typename == 'function':
            # Don't mess with magic functions
            if obj.__name__.find('__') == 0: return None
            path = (obj.__module__, prefix + obj.__name__)
            entry = [obj, path, 0, 0, timedelta(), timedelta()]
            self.data[id(obj)] = entry
            return self.wrap(entry, obj)
        
        if typename == 'classobj' or typename == 'type':
            if not hasattr(obj, '__dict__'):
                return None
            for k in obj.__dict__:
                oldv = obj.__dict__[k]
                newv = self.install_obj(obj.__name__ + '.', oldv)
                if newv:
                    setattr(obj, k, newv)
                    self.changelog.append([obj, k, oldv, newv])
        return None

    def wrap(self, entry, f):
        def wrapped(*args, **kwargs):
            if not self.enabled:
              return f(*args, **kwargs)

            inner_save = self.inner
            icalls_save = self.icalls
            self.inner = timedelta()
            self.icalls = 0

            start = datetime.now()
            ret = f(*args, **kwargs)
            finish = datetime.now()

            dt = finish - start
            entry[2] += 1
            entry[3] += self.icalls
            entry[4] = entry[4] + dt
            entry[5] = entry[5] + self.inner
            self.inner = inner_save + dt
            self.icalls = icalls_save + self.icalls + 1
            return ret
        wrapped.__dict__ = f.__dict__
        wrapped.__name__ = f.__name__
        wrapped.__original__ = f
        return wrapped


