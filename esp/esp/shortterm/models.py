from django.db import models

# Create your models here.

class ResponseForm(models.Model):
    contact_name = models.CharField(maxlength = 100)
    position = models.CharField(maxlength = 100)
    email = models.EmailField()
    school = models.CharField(maxlength = 150)
    mailing_address = models.TextField()
    xeroxable_flier_for_summer_hssp = models.BooleanField()
    xeroxable_flier_for_junction = models.BooleanField()
    catalog_of_all_2007_to_2008_esp_courses = models.BooleanField()
    xeroxable_fliers_for_all_2008_to_2009_esp_courses = models.BooleanField()
    splash_on_wheels_application = models.FileField(upload_to="uploaded/sow_apps/%y/", blank=True, null=True)
    bulk_financial_aid_application = models.FileField(upload_to="uploaded/bulk_finaid_form/%y/", blank=True, null=True)

    class Admin:
        pass

