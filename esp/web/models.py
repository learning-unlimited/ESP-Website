from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown

# Create your models here.

class NavBarEntry(models.Model):
    """ An entry for the secondary navigation bar """
    path = models.ForeignKey(DataTree)
    sort_rank = models.IntegerField()
    link = models.CharField(maxlength=256)
    text = models.CharField(maxlength=64)
    indent = models.BooleanField()
    
    def __str__(self):
        return ( self.path.full_name() + ':' + str(self.sort_rank) + ' (' + self.text + ')'  )
    
    class Admin:
        pass
    
    @staticmethod
    def find_by_url_parts(parts):
        """ Fetch a QuerySet of NavBarEntry objects by the url parts """
        # Get the Q_Web root
        Q_Web = GetNode('Q/Web')
        
        # Remove the last component
        parts.pop()
        
        # Find the branch
        try:
            branch = Q_Web.tree_decode( parts )
        except DataTree.NoSuchNodeException, ex:
            branch = ex.anchor
            if branch is None:
                raise NavBarEntry.DoesNotExist
            
        # Find the valid entries
        return NavBarEntry.objects.filter(path__rangestart__lte=branch.rangestart,path__rangeend__gte=branch.rangeend).order_by('sort_rank')
                                                                                                                                                                                                                                                                                                            
