""" Models for Resources application """



class ResourceType(models.Model):
    """ A type of resource
       e.g.: Projector, Classroom, Box of Chalk """

    description = models.TextField() # What is this resource?
    consumable  = models.BooleanField(default = False) # is this consummable?
    

class ResourceRequest(models.Model):
    " A request for a resource. There could be "
    
