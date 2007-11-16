from django.db import models

# Create your models here.

ONE_TO_FIVE_CHOICES = zip(range(1,6), range(1,6))

class BaseSplashSurveyRecord(models.Model):
    overall_experience = models.PositiveSmallIntegerField(choices=ONE_TO_FIVE_CHOICES, default=3)
    amount_learned = models.PositiveSmallIntegerField(choices=ONE_TO_FIVE_CHOICES, default=3)
    effectiveness_of_helpdesk_staff = models.PositiveSmallIntegerField(choices=ONE_TO_FIVE_CHOICES, default=3)
    effectiveness_of_security_staff = models.PositiveSmallIntegerField(choices=ONE_TO_FIVE_CHOICES, default=3)
    splash_photo = models.PositiveSmallIntegerField(choices=ONE_TO_FIVE_CHOICES, default=3)
    best_parts_of_program = models.TextField(blank=True)
    worst_parts_of_program = models.TextField(blank=True)
    


class EachMealSurveyRecord(models.Model):
    baseSurvey = models.ForeignKey(BaseSplashSurveyRecord)

class NoFoodSurveyRecord(models.Model):
    baseSurvey = models.ForeignKey(BaseSplashSurveyRecord)

class EachClassSurveyRecord(models.Model):
    baseSurvey = models.ForeignKey(BaseSplashSurveyRecord)
