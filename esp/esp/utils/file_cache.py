""" A cache system based on files. """

import os, time

from django.conf import settings
try:
    import cPickle as pickle
except ImportError:
    import pickle

BASE_DIR = settings.PROJECT_ROOT + 'file_cache/'

class FileCache(object):

    def __init__(self, piece_length=4, name=''):
        self.piece_length = piece_length
        self.base_dir = BASE_DIR + name + '/'

    def _get_file_name(self, key):
        key = str(key)
        chunks = []
        for i in range(0, len(key), self.piece_length):
            chunks.append(key[i:i + self.piece_length])
        return (self.base_dir + '/'.join(chunks[:-1]),
                chunks[-1] + '.tmp')

    def get(self, key, default=None):
        dir, file_name = self._get_file_name(key)
        try:
            f = open(dir + '/' + file_name, 'rb')
        except (IOError, OSError):
            return default
        try:
            expires_time, result_obj = pickle.load(f)
        except:
            return None
        else:
            if expires_time < time.time():
                print 'expired'
                return None
            
            return result_obj

    def delete(self, key):
        dir, file_name = self._get_file_name(key)
        try:
            os.remove(dir + '/' + file_name)
        except (OSError, IOError):
            pass

    def set(self, key, value, timeout=86400):
        dir, file_name = self._get_file_name(key)

        try:
            f = open(dir + '/' + file_name, 'wb')
        except (IOError, OSError):
            try:
                os.makedirs(dir)
            except (IOError, OSError):
                return
            else:
                try:
                    f = open(dir + '/' + file_name, 'wb')
                except (IOError, OSError):
                    return

        pickle.dump((time.time() + timeout,value), f, protocol=1)
