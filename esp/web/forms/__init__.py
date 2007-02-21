""" ESP In-house Form Fields ... some of these might be useful
    ouside ESP.
    """

from django import forms

class ResizeImageUploadField(forms.ImageUploadField):
    """ This field will allow one to upload a file, and that image
    to have a size to be resized to. """

    def __init__(self, size=None, *args, **kwargs):
        """ Give this a tuple size, like (128,128), and the image
            will be resized so that it is no larger than that box, but
            its aspect ratio is preserved. """
        
        forms.ImageUploadField.__init__(self, *args, **kwargs)
        self.size = size
        
    def prepare(self, new_data):
        """ gets the image and resizes it """
        if self.size is not None:
            from PIL import Image
            from cStringIO import StringIO
            try:
                content = new_data[self.field_name]['content']
            except:
                return new_data

            
            try:
                picturefile = StringIO()
                im = Image.open(StringIO(content))
                im.thumbnail(self.size, Image.ANTIALIAS)

                im.save(picturefile, im.format)
                content = picturefile.getvalue()
                
                picturefile.close()
            except:
                return new_data
            new_data[self.field_name]['content'] = content
        return new_data
