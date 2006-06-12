from django.db import models

# Create your models here.

root_path="/tmg/files"

class Media(models.Model):
    size = models.IntegerField()
    format = models.TextField()
    target_file = models.FileField(upload_to=root_path)
    def __str__(self):
        return str(self.target_file)

class Video(Media):
    pass

class Picture(Media):
    pass

class Project(models.Model):
    name = models.TextField()
    description = models.TextField(blank=True)
    sortorder = models.IntegerField(blank=True)
    def __str__(self):
        return str(name)

class Person(models.Model):
    name = models.TextField()
    def __str__(self):
        return str(name)

class ProjectVideoThunk(models.Model):
    project = models.ForeignKey(Project)
    video = models.ForeignKey(Video)
    thumbnail = models.ForeignKey(Picture)
    sortorder = models.IntegerField(blank=True)
    description = models.TextField()
    def __str__(self):
        return str(self.prject) + ': ' + str(self.video) + ' (' + str(self.description) + ')'

class ProjectAuthor(models.Model):
    person = models.ForeignKey(Person)
    project = models.ForeignKey(Project)
    sortorder = models.IntegerField(blank=True)
    def __str__(self):
        return str(self.project) + ': ' + str(self.person)

