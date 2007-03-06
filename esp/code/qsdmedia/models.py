from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.settings import MEDIA_ROOT

# Create your models here.

# The folder that Media files are saved to
root_file_path = "%y_%m/"

class Media(models.Model):
    """ A generic container for 'media': videos, pictures, papers, etc. """
    anchor = models.ForeignKey(DataTree) # Relevant node in the tree

    friendly_name = models.TextField() # Human-readable description of the media
    target_file = models.FileField(upload_to=root_file_path) # Target media file
    size = models.IntegerField(blank=True, null=True) # Size of the file, in bytes
    format = models.TextField(blank=True, null=True)  # Format string; should be human-readable (string format is currently unspecified)
    mime_type = models.CharField(blank=True, null=True, maxlength=256)
    file_extension = models.TextField(blank=True, null=True, maxlength=16) # Windows file extension for this file type, in case it's something archaic / Windows-centric enough to not get a unique MIME type

    def get_target_file_relative_url(self):
        return str(self.target_file)[ len(root_file_path): ]

    def __str__(self):
        return str(self.friendly_name)

    class Admin:
        pass
    
    @staticmethod
    def find_by_url_parts(parts, filename):
        """ Fetch a QSD record by its url parts """
        # Get the Q_Web root
        Q_Web = GetNode('Q/Web')

        # Find the branch
        try:
            branch = Q_Web.tree_decode( parts )
        except DataTree.NoSuchNodeException:
            raise Media.DoesNotExist

        # Find the record
        media = Media.objects.filter( anchor = branch, friendly_name = filename )
        if len(media) < 1:
            raise Media.DoesNotExist
        
        # Operation Complete!
        return media[0]


class Video(models.Model):
    """ Video media object
    
    This object should be a subclass of Media, except that subclassing is broken in Django.
    Contains basic metadata for a Video.
    """
    media = models.OneToOneField(Media) # the Media "superclass" instance; should be one-to-one

    container_format = models.TextField(blank=True, null=True) # This may become a ForeignKey to a list of known types; in the meantime, just enter the standard abbreviation for the type
    audio_codec = models.TextField(blank=True, null=True) # This may become a ForeignKey to a list of known types; in the meantime, just enter the standard abbreviation for the type
    video_codec = models.TextField(blank=True, null=True) # This may become a ForeignKey to a list of known types; in the meantime, just enter the standard abbreviation for the type

    bitrate = models.IntegerField(blank=True, null=True) # bitrate, in bits/second

    duration = models.IntegerField(blank=True, null=True) # length of the video, in seconds; this may become some sort of duration field at some point

    def __str__(self):
        return str(self.media)

    class Admin:
        pass

class Picture(models.Model):
    """ Picture media object
    
    This object should be a subclass of Media, except that subclassing is broken in Django.
    Contains basic metadata for a static picture.
    """
    media = models.OneToOneField(Media) # the Media "superclass" instance; should be one-to-one

    is_arbitrarily_resizable_format = models.BooleanField() # is the image a bitmap-based or vector-based format?

    x_resolution = models.IntegerField(blank=True, null=True) # Horizontal width of the Picture, in pixels
    y_resolution = models.IntegerField(blank=True, null=True) # Vertical height of the Picture, in pixels

    def __str__(self):
        return str(self.media)

    class Admin:
        pass

class PaperType(models.Model):
    """ A list of possible types of papers.  Each conference will typically have a set of types of papers that it accepts. """
    type_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.type_description)
    
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

    def __str__(self):
        return str(self.media)

    class Admin:
        pass


