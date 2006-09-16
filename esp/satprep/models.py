from django.db import models

# Create your models here.

class satprep(models.Model):
    """ Basic SAT Prep class, containing their minimal reg data """
    First_Name = models.CharField(maxlength=256)
    Last_Name = models.CharField(maxlength=256)
    Phone_Number = models.PhoneNumberField()
    Email_Address = models.EmailField()
    Street_Address = models.CharField(maxlength=512)
    City = models.CharField(maxlength=256)
    State = models.USStateField()
    Zip_Code = models.CharField(maxlength=5)
    Age = models.PositiveSmallIntegerField()
    Grade = models.PositiveSmallIntegerField()
    Year_Of_Graduation = models.PositiveSmallIntegerField()
    Emergency_Contact_First_Name = models.CharField(maxlength=256)
    Emergency_Contact_Last_Name = models.CharField(maxlength=256)
    Emergency_Contact_Phone = models.PhoneNumberField()
    Previous_SAT_Math_Score = models.PositiveSmallIntegerField()
    Previous_SAT_Reading_Score = models.PositiveSmallIntegerField()
    Previous_SAT_Writing_Score = models.PositiveSmallIntegerField()

    How_Did_You_Hear_About_SAT_Prep = models.TextField()

    Has_Paid = models.BooleanField()
    Has_Submitted_Forms = models.BooleanField()

    def __str__(self):
        return self.First_Name + " " + self.Last_Name
    
    class Admin:
        pass
    
