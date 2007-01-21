from django import forms




class ProfileManipulator(forms.Manipulator):
    def __init__(self):
        self.fields = (
            forms.
