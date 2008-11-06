from django import forms

from esp.qsd.models import QuasiStaticData
from esp.program.models import Program
from esp.datatree.models import *
from esp.db.fields import AjaxForeignKey
from esp.db.forms import AjaxForeignKeyNewformField

class QSDMoveForm(forms.Form):
    id = forms.IntegerField(widget=forms.HiddenInput)
    destination_path = AjaxForeignKeyNewformField(field=AjaxForeignKey(DataTree), label='Destination path', field_name='destination_path', help_text='Begin to type the tree location of the destination (starting with \'Q/\') and select the proper choice from the list that appears.')
    destination_name = forms.CharField(help_text='The file name that comes before the \'.html\' in the URL.  Preface with \'learn:\', \'teach:\', etc. to place under the corresponding section of the site.')
    
    def load_data(self, qsd):
        self.fields['id'].initial = qsd.id
        self.fields['destination_path'].initial = qsd.path.id
        self.fields['destination_name'].initial = qsd.name
        
    def save_data(self):
        #   Find all matching QSDs
        main_qsd = QuasiStaticData.objects.get(id=self.cleaned_data['id'])
        other_qsds = QuasiStaticData.objects.filter(path=main_qsd.path, name=main_qsd.name)
        for qsd in other_qsds:
            #   Move them over
            qsd.path = DataTree.objects.get(id=self.cleaned_data['destination_path'])
            qsd.name = self.cleaned_data['destination_name']
            qsd.save()

def destination_path(qsd_list):
    #   Compute lowest common anchor from qsd list
    path_ids = [q.path_id for q in qsd_list]
    path_data = DataTree.objects.filter(id__in=path_ids).values('rangestart', 'rangeend')
    starts = [d['rangestart'] for d in path_data]
    ends = [d['rangeend'] for d in path_data]
    range_min = min(starts)
    range_max = max(ends)
    common_anchors = DataTree.objects.filter(rangestart__lte=range_min, rangeend__gte=range_max).order_by('-rangestart', 'rangeend')
    if common_anchors.count() > 0:
        return common_anchors[0]
    else:
        return None

section_choices = (('learn', 'learn'), ('teach', 'teach'), ('manage', 'manage'), ('onsite', 'onsite'), ('', 'None'))

class QSDBulkMoveForm(forms.Form):
    id_list = forms.CharField(widget=forms.HiddenInput)
    destination_path = AjaxForeignKeyNewformField(field=AjaxForeignKey(DataTree), label='Destination path', field_name='destination_path', help_text='Begin to type the tree location of the destination (starting with \'Q/\') and select the proper choice from the list that appears.')
    alter_destinations = forms.BooleanField(required=False, initial=False, help_text='Check this only if you would like to change the section of the site (teach, learn, etc.) that the pages appear in.')
    destination_section = forms.ChoiceField(required=False, choices=section_choices, help_text='Choose \'None\' to eliminate the pages\' section designations, which will place them under /programs/ if they are associated with a program.')

    def load_data(self, qsd_list):
        anchor = destination_path(qsd_list)
        if anchor:
            self.fields['id_list'].initial = ','.join([str(q.id) for q in qsd_list])
            self.fields['destination_path'].initial = anchor.id
            return anchor
        else:
            return False
        
    def save_data(self):
        qsd_list = QuasiStaticData.objects.filter(id__in=[int(x) for x in self.cleaned_data['id_list'].split(',')])
        orig_anchor = destination_path(qsd_list)
        
        #   For each QSD in the list:
        for main_qsd in qsd_list:
            uri_orig = main_qsd.path.get_uri()
            #   Find its URI relative to the original anchor
            uri_relative = uri_orig[(len(orig_anchor.get_uri())):]
            #   Add that URI to that of the new anchor
            dest_tree = DataTree.objects.get(id=self.cleaned_data['destination_path'])
            uri_new = dest_tree.get_uri() + uri_relative
            #   Set the path
            other_qsds = QuasiStaticData.objects.filter(path=main_qsd.path, name=main_qsd.name)
            for qsd in other_qsds:
                #   Move them over
                qsd.path = DataTree.get_by_uri(uri_new, create=True)
            
                #   Now update the name if need be
                if self.cleaned_data['alter_destinations']:
                    name_parts = qsd.name.split(':')
                    if len(name_parts) > 1:
                        orig_section = name_parts[0]
                        orig_name = name_parts[1]
                    else:
                        orig_section = ''
                        orig_name = name_parts[0]
                        
                    new_section = self.cleaned_data['destination_section']
                    
                    if len(new_section) > 0:
                        qsd.name = new_section + ':' + orig_name
                    else:
                        qsd.name = orig_name
                        
                qsd.save()
