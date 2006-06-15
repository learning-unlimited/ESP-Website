from django.db import models
from tmg.core.models import Person, Project, Video, Picture

# Create your models here.

class Publication(models.Model):
    """ A publication, such as a paper.

    This is a container class; it can contain an arbitrary set of data (n papers, n videos, n pictures), and through PublicationStatus, these data are associated with a particular stage in the workflow of the publication. """
    title = models.TextField()
    bibtex_type = models.ForeignKey(BibTeXType) # BibTeX tye string; go google "BibTeX"
    bibtex_data = models.TextField() # A text field for BibTeX "key = value" entries

class PublicationStatus(models.Model):
    """ A stage in the workflow of a Publication.  See 'PublicationStatusType' for the possible stages """
    publication = models.ForeignKey(Publication) # A one-to-many relationship with Publications
    status = models.ForeignKey(PublicationStatusType)

class PaperType(models.Model):
    """ A list of possible types of papers.  Each conference will typically have a set of types of papers that it accepts. """
    type_description = models.TextField()

class BibTeXType(models.Model):
    """ A set of possible BibTeX bibliography types """
    type = models.TextField()

class Venue(models.Model):
    """ The venue that a conference or presentation takes place at, where a Publication is presented. """
    location = models.TextField() # Location, probably Address, of the venue.  Should be human-readable; not necessarily machine-parseable?
    start_date = models.DateTimeField(blank=True, null=True) # Start of the conference, if applicable
    end_date = models.DateTimeField(blank=True, null=True) # End of the conference, if applicable
    organization = models.TextField() # Organization hosting the event
    name = models.TextField() # Name of the venue, ie. "Star Trek Spock Lookalike Convention"
    additional_bibtex_data = models.ForeignKey(BibTeXType) # A text field for BibTeX "key = value" entries

class MediaType(models.Model):
    """ A fake, hacked implementation of the 'Media' superclass for the various media types.  Also forces a one-to-many association with a Publicaiton """
    target_publication = models.ForeignKey(PublicationStatus)
    friendly_name = models.TextField() # Human-readable, not machine-parseable, description of the media format (ie. "QuickTime, 640x480, encoded at High Quality with the h.264 and AAC codecs)
    mime_type = models.TextField()
    file_extension = models.TextField() # Windows file extension for this file type, in case it's something archaic / Windows-centric enough to not get a unique MIME type
    # General note: We probably need more identifying information for some of the Media classes; could that information just go inside those Media classes?

class PublicationAuthors(models.Model):
    """ Lists which people are authors to a particular publication.  A many-to-many relationship. """
    sort_order = models.IntegerField() # If there are multiple authors for a given paper, they should be shown in the sort order, lowest number to highest
    publication = models.ForeignKey(Publication)
    author = models.ForeignKey(Person)

class PublicationAssociatedProjects(models.Model):
    """ Nebulously associate a Publication with a Project.  The meaning of this association may become more specific in the future. """
    publication = models.ForeignKey(Publication)
    project = models.ForeignKey(Project)

class PublicationAssociatedMedia(models.Model):
    """ Associate a unit Media with a Publication.

    Ideally, this would be a one-to-many relationship, one publication to many media, but 'media' may include massive DV files that shouldn't be uploaded twice, but are related to multiple projects."""
    publication = models.ForeignKey(PublicationStatus)
    media = models.ForeignKey(Media)


class Media(models.Model):
    """  Ugly hack #n to get the lack of superclassing/subclassing to work """
    pass
