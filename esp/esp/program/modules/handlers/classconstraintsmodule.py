import logging
from django import forms
from django.db import transaction
from django.http import HttpResponseRedirect
from esp.program.models import ClassSubject, ScheduleConstraint, BooleanExpression, ScheduleTestSubject
from esp.program.modules.base import ProgramModuleObj, CoreModule, needs_admin, main_call
from esp.utils.web import render_to_response

logger = logging.getLogger(__name__)

class ClassConstraintsForm(forms.Form):
    CONSTRAINT_CHOICES = [
        ('prereq', 'Prerequisite (Class A requires Class B)'),
        ('mutual_exclusion', 'Mutual Exclusion (Class A and Class B cannot both be taken)'),
    ]
    
    class_a = forms.ModelChoiceField(queryset=ClassSubject.objects.none(), label="Class A")
    class_b = forms.ModelChoiceField(queryset=ClassSubject.objects.none(), label="Class B")
    constraint_type = forms.ChoiceField(choices=CONSTRAINT_CHOICES, initial='prereq')

    def __init__(self, program, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = program
        queryset = ClassSubject.objects.filter(parent_program=program).order_by('title')
        self.fields['class_a'].queryset = queryset
        self.fields['class_b'].queryset = queryset

class ClassConstraintsModule(ProgramModuleObj, CoreModule):
    """
    Module for managing complex class constraints like prerequisites and mutual exclusions.
    """
    
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Class Constraints",
            "module_type": "manage",
            "seq": 50,
            "choosable": 1,
        }

    @main_call
    @needs_admin
    def main(self, request, tl, one, two, module, extra, prog):
        context = {
            'prog': prog,
            'one': one,
            'two': two,
        }
        
        if request.method == 'POST':
            if 'add' in request.POST:
                form = ClassConstraintsForm(prog, request.POST)
                if form.is_valid():
                    self.add_constraint(prog, form.cleaned_data)
                    return HttpResponseRedirect(request.path)
            elif 'delete' in request.POST:
                constraint_id = request.POST.get('constraint_id')
                # Delete constraint and its expressions to avoid orphans
                constraints = ScheduleConstraint.objects.filter(id=constraint_id, program=prog)
                for constraint in constraints:
                    condition = constraint.condition
                    requirement = constraint.requirement
                    constraint.delete()
                    condition.delete()
                    requirement.delete()
                return HttpResponseRedirect(request.path)
        
        context['form'] = ClassConstraintsForm(prog)
        context['constraints'] = ScheduleConstraint.objects.filter(program=prog)
        
        return render_to_response(self.baseDir() + 'main.html', request, context)

    @transaction.atomic
    def add_constraint(self, program, data):
        class_a = data['class_a']
        class_b = data['class_b']
        ctype = data['constraint_type']
        
        if ctype == 'prereq':
            # IF Class A THEN Class B
            cond_label = f"Enrolled in {class_a.title} ({class_a.id})"
            req_label = f"Enrolled in {class_b.title} ({class_b.id})"
            
            cond = BooleanExpression.objects.create(label=cond_label)
            req = BooleanExpression.objects.create(label=req_label)
            
            # Create the tokens
            ScheduleTestSubject.objects.create(exp=cond, subject=class_a, text=f"In {class_a.title}", seq=0)
            ScheduleTestSubject.objects.create(exp=req, subject=class_b, text=f"In {class_b.title}", seq=0)
            
            ScheduleConstraint.objects.create(program=program, condition=cond, requirement=req)
            
        elif ctype == 'mutual_exclusion':
            # IF Class A THEN NOT Class B
            cond_label = f"Enrolled in {class_a.title} ({class_a.id})"
            req_label = f"NOT enrolled in {class_b.title} ({class_b.id})"
            
            cond = BooleanExpression.objects.create(label=cond_label)
            req = BooleanExpression.objects.create(label=req_label)
            
            ScheduleTestSubject.objects.create(exp=cond, subject=class_a, text=f"In {class_a.title}", seq=0)
            
            ScheduleTestSubject.objects.create(exp=req, subject=class_b, text=f"In {class_b.title}", seq=0)
            # Add NOT operator
            from esp.program.models import BooleanToken
            BooleanToken.objects.create(exp=req, text="NOT", seq=10)
            
            ScheduleConstraint.objects.create(program=program, condition=cond, requirement=req)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
