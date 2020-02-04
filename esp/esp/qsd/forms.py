from django import forms

from esp.web.models import NavBarCategory
from esp.qsd.models import QuasiStaticData
from esp.program.models import Program
from esp.db.fields import AjaxForeignKey
from esp.db.forms import AjaxForeignKeyNewformField

import os.path

class QSDMoveForm(forms.Form):
    id = forms.IntegerField(widget=forms.HiddenInput)
    nav_category = forms.ChoiceField(choices=(), label='Navigation category')
    destination = forms.CharField(help_text='The portion of the URL that comes before the \'.html\'.')

    def __init__(self, *args, **kwargs):
        super(QSDMoveForm, self).__init__(*args, **kwargs)
        self.fields['nav_category'].choices = [(n.id, n.name) for n in NavBarCategory.objects.all()]

    def load_data(self, qsd):
        self.fields['id'].initial = qsd.id
        self.fields['destination'].initial = qsd.url
        self.fields['nav_category'].initial = qsd.nav_category

    def save_data(self):
        #   Find all matching QSDs
        main_qsd = QuasiStaticData.objects.get(id=self.cleaned_data['id'])
        other_qsds = QuasiStaticData.objects.filter(url=main_qsd.url, name=main_qsd.name)
        for qsd in other_qsds:
            #   Move them over
            qsd.url = self.cleaned_data['destination']
            qsd.nav_category = NavBarCategory.objects.get(id=self.cleaned_data['nav_category'])
            qsd.save()

def destination_path(qsd_list):
    #   Compute longest common URL substring (at beginning) from qsd list
    urls = [q.url for q in qsd_list]
    prefix = os.path.commonprefix(urls)
    return '/'.join(prefix.split('/')[:-1])

section_choices = (('learn', 'learn'), ('teach', 'teach'), ('manage', 'manage'), ('onsite', 'onsite'), ('', 'None'))

class QSDBulkMoveForm(forms.Form):
    id_list = forms.CharField(widget=forms.HiddenInput)
    destination = forms.CharField(label='Destination')

    def load_data(self, qsd_list):
        target_path = destination_path(qsd_list)
        if target_path:
            self.fields['id_list'].initial = ','.join([str(q.id) for q in qsd_list])
            self.fields['destination'].initial = target_path
            return target_path
        else:
            return False

    def save_data(self):
        qsd_list = QuasiStaticData.objects.filter(id__in=[int(x) for x in self.cleaned_data['id_list'].split(',')])
        orig_path = destination_path(qsd_list)

        #   For each QSD in the list:
        for main_qsd in qsd_list:

            #   Find its URI relative to the original
            url_relative = main_qsd.url[len(orig_path):]
            #   Add that URI to that of the new one
            url_new = self.cleaned_data['destination'] + url_relative

            #   Set the path on all versions of this QSD
            other_qsds = QuasiStaticData.objects.filter(url=main_qsd.url, name=main_qsd.name)
            for qsd in other_qsds:
                #   Move them over
                qsd.url = url_new
                qsd.save()
