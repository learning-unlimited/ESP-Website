from django import forms
from esp.middleware import ESPError

class SplashInfoForm(forms.Form):
    satchoices = [('no', 'No thanks; I will bring my own lunch'), 
                  ('classic_club', 'Yes, Classic Club (turkey/bacon/ham/cheddar)'), 
                  ('honey_chicken', 'Yes, Honey Chicken (chicken/honey mustard)'),
                  ('veggie', 'Yes, Veggie (guacamole/olives/mozzarella/cheddar)')]

    sunchoices = [('no', 'No thanks; I will bring my own lunch'),
                  ('cheese', 'Yes, Cheese Pizza'),
                  ('pepperoni', 'Yes, Pepperoni Pizza')]
                  
    discount_choices = [(False, 'I am the first in my household enrolling in Splash (+ $40)'),
                        (True, 'I have a brother/sister already enrolled in Splash  (+ $20).')]
                  
    lunchsat = forms.ChoiceField(choices=satchoices)
    lunchsun = forms.ChoiceField(choices=sunchoices)
    siblingdiscount = forms.ChoiceField(choices=discount_choices, widget=forms.RadioSelect)
    siblingname = forms.CharField(max_length=128, required=False)
    
    def load(self, splashinfo):
        self.initial['lunchsat'] = splashinfo.lunchsat
        self.initial['lunchsun'] = splashinfo.lunchsun
        self.initial['siblingdiscount'] = splashinfo.siblingdiscount
        self.initial['siblingname'] = splashinfo.siblingname

    def save(self, splashinfo):
        splashinfo.lunchsat = self.cleaned_data['lunchsat']
        splashinfo.lunchsun = self.cleaned_data['lunchsun']
        splashinfo.siblingdiscount = bool(self.cleaned_data['siblingdiscount'])
        splashinfo.siblingname = self.cleaned_data['siblingname']
        splashinfo.submitted = True
        splashinfo.save()
        
