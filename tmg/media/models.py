from django.db import models

# Create your models here.

# The folder that Media files are saved to
root_file_path = '/tmg/video/web/kiosk/media/%Y_%m'

class Media(models.Model):
    """ A generic container for 'media': videos, pictures, papers, etc. """
    size = models.IntegerField() # Size of the file, in bytes
    format = models.TextField()  # Format string; should be human-readable (string format is currently unspecified)
    mime_type = models.TextField()
    file_extension = models.TextField() # Windows file extension for this file type, in case it's something archaic / Windows-centric enough to not get a unique MIME type

    friendly_name = models.TextField() # Human-readable description of the media

    def __str__(self):
        return str(self.target_file)

    target_file = models.FileField(upload_to=root_file_path) # Target media file

    class Admin:
        pass

class Video(models.Model):
    """ Video media object
    
    This object should be a subclass of Media, except that subclassing is broken in Django.
    Contains basic metadata for a Video.
    """
    media = models.OneToOneField(Media) # the Media "superclass" instance; should be one-to-one

    container_format = models.TextField(blank=True) # This may become a ForeignKey to a list of known types; in the meantime, just enter the standard abbreviation for the type
    audio_codec = models.TextField(blank=True) # This may become a ForeignKey to a list of known types; in the meantime, just enter the standard abbreviation for the type
    video_codec = models.TextField(blank=True) # This may become a ForeignKey to a list of known types; in the meantime, just enter the standard abbreviation for the type

    bitrate = models.IntegerField() # bitrate, in bits/second

    duration = models.IntegerField() # length of the video, in seconds; this may become some sort of duration field at some point

    class Admin:
        pass

class Picture(models.Model):
    """ Picture media object
    
    This object should be a subclass of Media, except that subclassing is broken in Django.
    Contains basic metadata for a static picture.
    """
    media = models.OneToOneField(Media) # the Media "superclass" instance; should be one-to-one

    is_arbitrarily_resizable_format = models.BooleanField() # is the image a bitmap-based or vector-based format?

    x_resolution = models.IntegerField() # Horizontal width of the Picture, in pixels
    y_resolution = models.IntegerField() # Vertical height of the Picture, in pixels

    class Admin:
        pass

class PaperType(models.Model):
    """ A list of possible types of papers.  Each conference will typically have a set of types of papers that it accepts. """
    type_description = models.TextField()
    
    class Admin:
        pass

class Paper(models.Model):
    """ Paper media object
    
    This object should be a subclass of Media, except that subclassing is broken in Django.
    Contains basic metadata for a paper, typically (though not necessarily) submitted to a conference or publication.
    """

    is_mutable_text = models.BooleanField() # Is the text alterable?, or is it in a locked format like a PDF or a locked MS Office document
    type = models.ForeignKey(PaperType) # Type of the paper, from a list of officially-acknowledged "types"

    media = models.OneToOneField(Media)

    class Admin:
        pass


