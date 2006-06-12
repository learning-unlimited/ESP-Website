from django.db import models

# Create your models here.

video_path='/tmg/video/web/kiosk/media/videos/'
picture_path='/tmg/video/web/kiosk/media/pictures/'

class Media(models.Model):
    size = models.IntegerField()
    format = models.TextField()

    def __str__(self):
        return str(self.target_file)
    class Admin:
        pass

class Video(Media):
    target_file = models.FileField(upload_to=video_path)
    root_path = video_path
    class Admin:
        pass

class Picture(Media):
    target_file = models.FileField(upload_to=picture_path)
    class Admin:
        pass

class Project(models.Model):
    name = models.TextField()
    description = models.TextField(blank=True)
    sortorder = models.IntegerField(blank=True)
    menu_thumbnail = models.ForeignKey(Picture)
    def __str__(self):
        return str(name)
    class Admin:
        pass

class Person(models.Model):
    name = models.TextField()
    def __str__(self):
        return str(name)
    class Admin:
        pass

class ProjectVideoThunk(models.Model):
    project = models.ForeignKey(Project)
    video = models.ForeignKey(Video)
    thumbnail = models.ForeignKey(Picture)
    sortorder = models.IntegerField(blank=True)
    description = models.TextField()
    def __str__(self):
        return str(self.prject) + ': ' + str(self.video) + ' (' + str(self.description) + ')'
    class Admin:
        pass

class ProjectAuthor(models.Model):
    person = models.ForeignKey(Person)
    project = models.ForeignKey(Project)
    sortorder = models.IntegerField(blank=True)
    def __str__(self):
        return str(self.project) + ': ' + str(self.person)
    class Admin:
        pass
