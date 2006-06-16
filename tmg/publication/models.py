from django.db import models
from tmg.media.models import Media
from tmg.core.models import Person, Project

# Create your models here.

class BibTeXType(models.Model):
    """ A set of possible BibTeX bibliography types """
    type = models.TextField()

    class Admin:
        pass

class Publication(models.Model):
    """ A publication, such as a paper.

    This is a container class; it can contain an arbitrary set of data (n papers, n videos, n pictures), and through PublicationStatus, these data are associated with a particular stage in the workflow of the publication. """
    title = models.TextField()
    bibtex_type = models.ForeignKey(BibTeXType) # BibTeX tye string; go google "BibTeX"
    bibtex_data = models.TextField() # A text field for BibTeX "key = value" entries

    class Admin:
        pass

class PublicationStatusType(models.Model):
    """ An A-list of possible publication status types.  This will be static; it's just there so that the relevant strings are readily accessible. """
    type = models.TextField()

    class Admin:
        pass
    
class PublicationStatus(models.Model):
    """ A stage in the workflow of a Publication.  See 'PublicationStatusType' for the possible stages """
    publication = models.ForeignKey(Publication) # A one-to-many relationship with Publications
    status = models.ForeignKey(PublicationStatusType)
    media_blob = models.ManyToManyField(Media)

    class Admin:
        pass

class PaperType(models.Model):
    """ A list of possible types of papers.  Each conference will typically have a set of types of papers that it accepts. """
    type_description = models.TextField()

    class Admin:
        pass

class Venue(models.Model):
    """ The venue that a conference or presentation takes place at, where a Publication is presented. """
    location = models.TextField() # Location, probably Address, of the venue.  Should be human-readable; not necessarily machine-parseable?
    start_date = models.DateTimeField(blank=True, null=True) # Start of the conference, if applicable
    end_date = models.DateTimeField(blank=True, null=True) # End of the conference, if applicable
    organization = models.TextField() # Organization hosting the event
    name = models.TextField() # Name of the venue, ie. "Star Trek Spock Lookalike Convention"
    additional_bibtex_data = models.ForeignKey(BibTeXType) # A text field for BibTeX "key = value" entries

    class Admin:
        pass

class PublicationAuthors(models.Model):
    """ Lists which people are authors to a particular publication.  A many-to-many relationship. """
    sort_order = models.IntegerField() # If there are multiple authors for a given paper, they should be shown in the sort order, lowest number to highest
    publication = models.ForeignKey(Publication)
    author = models.ForeignKey(Person)

    class Admin:
        pass

class PublicationAssociatedProjects(models.Model):
    """ Nebulously associate a Publication with a Project.  The meaning of this association may become more specific in the future. """
    publication = models.ForeignKey(Publication)
    project = models.ForeignKey(Project)

    class Admin:
        pass
