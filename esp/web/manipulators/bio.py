from django import forms
from django.core import validators
from esp.web.forms import ResizeImageUploadField

import re

class TeacherBioManipulator(forms.Manipulator):
    def __init__(self):

        self.fields = (
            forms.TextField(field_name="slugbio", length=55, maxlength=128),
            forms.LargeTextField(field_name="bio", rows=20, cols=60),
            ResizeImageUploadField(field_name="picture", size=(300,300))
        )
