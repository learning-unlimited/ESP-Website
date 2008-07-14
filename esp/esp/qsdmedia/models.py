
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.settings import MEDIA_ROOT
from esp.db.fields import AjaxForeignKey


# Create your models here.

# The folder that Media files are saved to
root_file_path = "uploaded/%y_%m"

class Media(models.Model):
    """ A generic container for 'media': videos, pictures, papers, etc. """
    anchor = AjaxForeignKey(DataTree) # Relevant node in the tree
    friendly_name = models.TextField() # Human-readable description of the media
    target_file = models.FileField(upload_to=root_file_path) # Target media file
    size = models.IntegerField(blank=True, null=True, editable=False) # Size of the file, in bytes
    format = models.TextField(blank=True, null=True)  # Format string; should be human-readable (string format is currently unspecified)
    mime_type = models.CharField(blank=True, null=True, max_length=256, editable=False)
    file_extension = models.TextField(blank=True, null=True, max_length=16, editable=False) # Windows file extension for this file type, in case it's something archaic / Windows-centric enough to not get a unique MIME type

    #def get_target_file_relative_url(self):a
    #    return str(self.target_file)[ len(root_file_path): ]

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
    media = models.ForeignKey(Media, unique=True) # the Media "superclass" instance; should be one-to-one

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
    media = models.ForeignKey(Media, unique=True) # the Media "superclass" instance; should be one-to-one

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

    media = models.ForeignKey(Media, unique=True)

    def __str__(self):
        return str(self.media)

    class Admin:
        pass



