from django.db import models
from tmg.core.models import Person, Project, Video, Picture

# Create your models here.

class Publication(models.Model):
    title = models.TextField()
    bibtex_type = models.ForeignKey(BibTeXType)
    bibtex_data = models.TextField()

class PublicationStatus(models.Model):
    publication = models.ForeignKey(Publication)
    status = models.ForeignKey(PublicationStatusType)

class PaperType(models.Model):
    type_description = models.TextField()

class BibTeXType(models.Model):
    type = models.TextField()

class Venue(models.Model):
    location = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    organization = models.TextField()
    name = models.TextField()
    additional_bibtex_data = models.ForeignKey(BibTeXType)

class MediaType(models.Model):
    target_publication = models.ForeignKey(PublicationStatus)
    friendly_name = models.TextField()
    mime_type = models.TextField()
    file_extension = models.TextField()

class PublicationAuthors(models.Model):
    sort_order = models.IntegerField()
    publication = models.ForeignKey(Publication)
    author = models.ForeignKey(Person)

class PublicationAssociatedProjects(models.Model):
    publication = models.ForeignKey(Publication)
    project = models.ForeignKey(Project)

class PublicationAssociatedMedia(models.Model):
    publication = models.ForeignKey(PublicationStatus)
    media = models.ForeignKey(Media)

class Media(models.Model):
    pass
