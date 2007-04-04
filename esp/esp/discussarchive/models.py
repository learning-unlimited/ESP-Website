from django.db import models


class ArchiveEmail(models.Model):


    mail_list = models.ForeignKey('ArchiveList')
    thread  = models.ForeignKey('ArchiveThread')

    body      = models.TextField()
    subject   = models.TextField()
    fromfield = models.TextField()
    bcc       = models.TextField(blank=True,null=True)
    cc        = models.TextField(blank=True,null=True)
    ts        = models.DateField(auto_now = True)
    extra_headers = models.TextField(blank=True,null=True)

    rating  = models.IntegerField()




    class Admin:
        pass

class ArchiveThread(models.Model):
    subject = models.TextField()

    class Admin:
        pass


class ArchiveList(models.Model):
    list_name = models.TextField()

    class Admin:
        pass
