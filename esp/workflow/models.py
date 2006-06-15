from django.db import models

# Create your models here.

# Argh: No virtual classes in Python?
class Controller:
    """ A generic virtual superclass, that all Controllers inherit from """
    def run(self, data):
        """ Do some action based on a given chunk of data """
        pass


        
