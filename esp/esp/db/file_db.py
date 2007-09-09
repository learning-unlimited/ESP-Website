""" The FileDBManager allows one to use a File interface embedded
in a Django DB model.

An example usage::

    class MyModel(models.Model):
        objects = FileDBManager(4, 'MyModel')
        cool_name = models.CharField(maxlength=255)
        other_info = models.TextField()

        def get_file_id(self):
            # Used to override what file it's saved in!
            return self.cool_name

    >>> a = MyModel(1, 'yey', 'sfasdf some text asfafwef')
    >>> MyModel.objects.obj_to_file(a)

    >>> MyModel.objects.get_by_id('yey')
    <__main__.MyModel object at 0x234123>
""" 

import os

from django.db import models
from django.conf import settings

try:
    import cPickle as pickle
except ImportError:
    import pickle

__all__ = ['FileDBManager']

BASE_DIR = settings.PROJECT_ROOT + 'file_db/'

class FileDBManager(models.Manager):

    def __init__(self, piece_length=4, name=''):
        self.piece_length = piece_length
        super(FileDBManager, self).__init__()
        self.base_dir = BASE_DIR + name + '/'

    def get_path_by_id(self, pk):
        pk = str(pk)
        chunks = []
        for i in range(0, len(pk), self.piece_length):
            chunks.append(pk[i:i + self.piece_length])
        return (self.base_dir + '/'.join(chunks[:-1]),
                chunks[-1] + '.dat')

    def get_by_id_list(self, pks):
        result = []
        for pk in pks:
            current = self.get_by_id(pk)
            if current is not None:
                result.append(current)

        return result

    def move_all_to_file(self):
        """ Move all the the objects in this to files. """
        for item in self.all():
            self.obj_to_file(item)

    def clear_all_files(self, pk):
        import shutil
        dir = self.get_path_by_id(' ')[0]
        shutil.rmtree(dir, True)

    def get_by_id(self, pk):
        dir, file_name = self.get_path_by_id(pk)
        try:
            f = open(dir + '/' + file_name, 'rb')
        except (IOError, OSError):
            return None
        try:
            result_obj = pickle.load(f)
        except:
            return None
        else:
            return result_obj

    def obj_to_file(self, obj):
        if hasattr(obj, 'get_file_id'):
            pk = obj.get_file_id()
        else:
            pk = obj._get_pk_val()

        dir, file_name = self.get_path_by_id(pk)
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
        pickle.dump(obj, f, protocol=1)
