from django.db import models
from django.contrib.auth.models import User
from tmg.media.models import Media, Picture, Video

# Create your models here.

class Project(models.Model):
    """ A Video Kiosk 'Project'.  Contains, or is linked to by, all data needed by a Video Kiosk screen """
    name = models.TextField() # A short name describing the project; ideally, one word, no spaces
    description = models.TextField(blank=True) # A short description of the project; ideally, one sentence
    sortorder = models.IntegerField(blank=True, null=True) # Numerical sort order, if multiple projects exist; lowest number goes first
    menu_thumbnail = models.ForeignKey(Picture) # A thumbnail image icon that represents the project
    def __str__(self):
        return str(self.name)
    class Admin:
        pass

class Person(models.Model):
    """ Represents a real, live person, participating in Projects.  The person can be associated with a Django user. """
    name = models.TextField() # Person's full name, as shown in a paper's "Author" field
    user = models.ForeignKey(User, blank=True, null=True) # Django user associated with this Person; should be a one-to-one relationship
    def __str__(self):
        return str(self.name)
    class Admin:
        pass

class ProjectVideoThunk(models.Model):
    """ Associates a Project with its Video, along with some required metadata

    This should be a one-to-many association, Video-to-Project """
    project = models.ForeignKey(Project)
    video = models.ForeignKey(Video)
    thumbnail = models.ForeignKey(Picture) # Thumbnail icon representing the video; very likely the same icon that represents the project, though this isn't required
    sortorder = models.IntegerField(blank=True, null=True)
    short_description = models.TextField() # Short text description of the video; should be order of one sentence
    def __str__(self):
        return str(self.project) + ': ' + str(self.video) + ' (' + str(self.short_description) + ')'
    class Admin:
        pass

class ProjectAuthor(models.Model):
    """ Assocates a person as the author of a paper.  A many-to-many relationship. """
    person = models.ForeignKey(Person)
    project = models.ForeignKey(Project)
    sortorder = models.IntegerField(blank=True) # If multiple people are associated with a project, they are listed as ordered by sortorder, lowest values first
    def __str__(self):
        return str(self.project) + ': ' + str(self.person)
    class Admin:
        pass
