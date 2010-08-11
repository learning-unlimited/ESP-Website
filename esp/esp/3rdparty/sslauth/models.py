from django.db import models
from django.contrib.auth.models import User

class DistinguishedName(models.Model):
    cn = models.CharField(max_length=255)
    o = models.CharField(max_length=255, blank=True)
    ou = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=255, blank=True)
    c = models.CharField(max_length=255, blank=True)
    st = models.CharField(max_length=255, blank=True)
    l = models.CharField(max_length=255, blank=True)
    t = models.CharField(max_length=255, blank=True)
    i = models.CharField(max_length=255, blank=True)
    g = models.CharField(max_length=255, blank=True)
    s = models.CharField(max_length=255, blank=True)
    d = models.CharField(max_length=255, blank=True)
    uid = models.CharField(max_length=255, blank=True)
    
    def __unicode__(self):
        vals = [ "%s=%s" % (key, self.__getattribute__(key.lower())) for key in ( 'CN', 'OU', 'O', 'C', 'Email' ) if self.__getattribute__(key.lower()) ]
        return "/".join(vals)
            
    class Admin:
        pass

class ClientCertificate(models.Model):
    serial = models.CharField(max_length=255, blank=True)
    subject = models.ForeignKey(DistinguishedName, related_name='subject')
    issuer = models.ForeignKey(DistinguishedName, related_name='issuer', blank=True, null=True)
    cert = models.TextField(blank=True)
    user = models.ForeignKey(User)
    
    def __unicode__(self):
        return "%s, %s, %s" % (self.subject.cn, self.subject.email, self.subject.o)
    
    class Admin:
        pass
