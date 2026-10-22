__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
from django import forms
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from esp.program.models import (
    BooleanExpression, BooleanToken, ClassSubject,
    ScheduleConstraint, ScheduleTestSubject,
)
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web import render_to_response


class ClassConstraintsForm(forms.Form):
    CONSTRAINT_CHOICES = [
        ('requires', 'Requires (students taking Class A must also take Class B)'),
        ('mutual_exclusion', 'Mutual Exclusion (students cannot take both Class A and Class B)'),
    ]

    class_a = forms.ModelChoiceField(queryset=ClassSubject.objects.none(), label="Class A")
    class_b = forms.ModelChoiceField(queryset=ClassSubject.objects.none(), label="Class B")
    constraint_type = forms.ChoiceField(choices=CONSTRAINT_CHOICES, initial='requires')

    def __init__(self, program, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = program
        queryset = ClassSubject.objects.filter(parent_program=program).order_by('title')
        self.fields['class_a'].queryset = queryset
        self.fields['class_b'].queryset = queryset

    def clean(self):
        cleaned_data = super().clean()
        class_a = cleaned_data.get('class_a')
        class_b = cleaned_data.get('class_b')
        # A class constrained against itself is either redundant or blocks
        # all enrollment in it.
        if class_a and class_b and class_a == class_b:
            raise forms.ValidationError(
                "Class A and Class B must be different. "
                "A class cannot have a constraint with itself."
            )
        return cleaned_data


class ClassConstraintsModule(ProgramModuleObj):
    doc = """Require or forbid taking one class together with another."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Class Constraints",
            "link_title": "Manage Class Constraints",
            "module_type": "manage",
            "seq": 50,
            "choosable": 1,
        }

    @main_call
    @needs_admin
    def class_constraints(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            if 'add' in request.POST:
                form = ClassConstraintsForm(prog, request.POST)
                if form.is_valid():
                    self.add_constraint(prog, form.cleaned_data)
                    return HttpResponseRedirect(request.path)
                # Re-render with validation errors
                return self._render(request, prog, form)

            elif 'delete' in request.POST:
                try:
                    constraint_id = int(request.POST.get('constraint_id', ''))
                except (ValueError, TypeError):
                    return HttpResponseBadRequest("Invalid constraint ID.")
                self._delete_constraint(constraint_id, prog)
                return HttpResponseRedirect(request.path)

        return self._render(request, prog, ClassConstraintsForm(prog))

    def _render(self, request, prog, form):
        context = {
            # manage_base.html builds its breadcrumb from `program`
            'program': prog,
            'form': form,
            'constraints': self.get_constraints(prog).select_related('condition', 'requirement'),
        }
        return render_to_response(self.baseDir() + 'main.html', request, context)

    @staticmethod
    def get_constraints(prog):
        """ Constraints created by this module, i.e. built from ScheduleTestSubject tokens. """
        subject_exps = ScheduleTestSubject.objects.values('exp_id')
        return ScheduleConstraint.objects.filter(program=prog, condition_id__in=subject_exps)

    @transaction.atomic
    def _delete_constraint(self, constraint_id, prog):
        """ Delete one of this module's constraints, keeping any expression
            that another constraint still uses. """
        constraint = self.get_constraints(prog).filter(id=constraint_id).first()
        if constraint is not None:
            constraint.delete_with_expressions()

    @transaction.atomic
    def add_constraint(self, program, data):
        class_a = data['class_a']
        class_b = data['class_b']

        # Requirement labels complete the student-facing error message
        # "Adding X to your schedule requires that you <label>."
        if data['constraint_type'] == 'requires':
            # Encode: IF enrolled(A) THEN enrolled(B)
            requirement = self._subject_expression("also take", class_b)
        elif data['constraint_type'] == 'mutual_exclusion':
            # Encode: IF enrolled(A) THEN NOT enrolled(B)
            requirement = self._subject_expression("not take", class_b, negate=True)

        ScheduleConstraint.objects.create(
            program=program,
            condition=self._subject_expression("take", class_a),
            requirement=requirement,
            # on_failure code is no longer executed; empty avoids a warning
            on_failure='',
        )

    @staticmethod
    def _subject_expression(verb, subject, negate=False):
        # BooleanExpression.label is max_length=80; truncate the title, not the code
        label = f"{verb} {subject.emailcode()}: {subject.title}"[:80]
        expression = BooleanExpression.objects.create(label=label)
        ScheduleTestSubject.objects.create(exp=expression, subject=subject,
                                           text=f"enrolled_in_{subject.id}", seq=0)
        if negate:
            # Stack: [ScheduleTestSubject at seq=0, "NOT" at seq=10]
            BooleanToken.objects.create(exp=expression, text="NOT", seq=10)
        return expression

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
