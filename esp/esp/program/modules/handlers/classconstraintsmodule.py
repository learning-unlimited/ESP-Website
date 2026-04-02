import logging
from django import forms
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from esp.program.models import (
    BooleanExpression, BooleanToken, ClassSubject,
    ScheduleConstraint, ScheduleTestSubject,
)
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

    def clean(self):
        cleaned_data = super().clean()
        class_a = cleaned_data.get('class_a')
        class_b = cleaned_data.get('class_b')
        # Fix: reject identical class selection to prevent always-unsatisfiable
        # or vacuously-true constraints.
        if class_a and class_b and class_a == class_b:
            raise forms.ValidationError(
                "Class A and Class B must be different. "
                "A class cannot have a constraint with itself."
            )
        return cleaned_data


class ClassConstraintsModule(ProgramModuleObj, CoreModule):
    """
    Module for managing complex class constraints like prerequisites and
    mutual exclusions. Constraints are represented as ScheduleConstraints
    using BooleanExpressions composed of ScheduleTestSubject tokens.
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
            # Fix: manage_base.html uses {{ program.getUrlBase }}; pass both
            # so the breadcrumb link renders correctly.
            'program': prog,
            'one': one,
            'two': two,
        }

        if request.method == 'POST':
            if 'add' in request.POST:
                form = ClassConstraintsForm(prog, request.POST)
                if form.is_valid():
                    self.add_constraint(prog, form.cleaned_data)
                    return HttpResponseRedirect(request.path)
                # Re-render with validation errors
                context['form'] = form
                context['constraints'] = ScheduleConstraint.objects.filter(program=prog)
                return render_to_response(self.baseDir() + 'main.html', request, context)

            elif 'delete' in request.POST:
                raw_id = request.POST.get('constraint_id', '')
                # Fix: validate/cast before querying to avoid ValueError 500s.
                try:
                    constraint_id = int(raw_id)
                except (ValueError, TypeError):
                    return HttpResponseBadRequest("Invalid constraint ID.")
                self._delete_constraint(constraint_id, prog)
                return HttpResponseRedirect(request.path)

        context['form'] = ClassConstraintsForm(prog)
        context['constraints'] = ScheduleConstraint.objects.filter(program=prog)
        return render_to_response(self.baseDir() + 'main.html', request, context)

    @transaction.atomic
    def _delete_constraint(self, constraint_id, prog):
        """
        Safely delete a ScheduleConstraint and its associated
        BooleanExpressions only if they are not referenced by any other
        ScheduleConstraint rows.

        Fix: The previous implementation unconditionally deleted expressions,
        which could cascade-kill unrelated constraints sharing an expression.
        """
        try:
            constraint = ScheduleConstraint.objects.get(id=constraint_id, program=prog)
        except ScheduleConstraint.DoesNotExist:
            return

        condition_id = constraint.condition_id
        requirement_id = constraint.requirement_id

        # Delete the constraint first; CASCADE on the FK goes the other way
        # (expression → constraint), so this is safe.
        constraint.delete()

        # Only delete the expression if no other ScheduleConstraint now
        # references it (condition or requirement).
        for expr_id in (condition_id, requirement_id):
            still_referenced = ScheduleConstraint.objects.filter(
                Q(condition_id=expr_id) | Q(requirement_id=expr_id)
            ).exists()
            if not still_referenced:
                BooleanExpression.objects.filter(id=expr_id).delete()

    @transaction.atomic
    def add_constraint(self, program, data):
        class_a = data['class_a']
        class_b = data['class_b']
        ctype = data['constraint_type']

        # Fix: BooleanExpression.label is max_length=80. Class titles are
        # unbounded TextFields, so truncate to avoid DB errors.
        def _make_label(prefix, cls):
            label = f"{prefix} {cls.title} (id={cls.id})"
            return label[:80]

        # Fix: on_failure must be a syntactically valid Python function body
        # so exec() inside ScheduleConstraint.handle_failure() doesn't raise
        # SyntaxError on every constraint violation.
        _on_failure = 'return (None, None)'

        # Human-readable token text uses the class id (a short, stable value)
        # so it also stays within the BooleanToken.text field length.
        def _token_text(cls):
            return f"enrolled_in_{cls.id}"

        if ctype == 'prereq':
            # Encode: IF enrolled(A) THEN enrolled(B)
            cond = BooleanExpression.objects.create(label=_make_label("Enrolled in", class_a))
            req = BooleanExpression.objects.create(label=_make_label("Enrolled in", class_b))

            ScheduleTestSubject.objects.create(exp=cond, subject=class_a,
                                               text=_token_text(class_a), seq=0)
            ScheduleTestSubject.objects.create(exp=req, subject=class_b,
                                               text=_token_text(class_b), seq=0)

            ScheduleConstraint.objects.create(
                program=program, condition=cond, requirement=req,
                on_failure=_on_failure,
            )

        elif ctype == 'mutual_exclusion':
            # Encode: IF enrolled(A) THEN NOT enrolled(B)
            # Stack for requirement: [ScheduleTestSubject(B) at seq=0,
            #                         BooleanToken("NOT")   at seq=10]
            cond = BooleanExpression.objects.create(label=_make_label("Enrolled in", class_a))
            req = BooleanExpression.objects.create(
                label=_make_label("NOT enrolled in", class_b)
            )

            ScheduleTestSubject.objects.create(exp=cond, subject=class_a,
                                               text=_token_text(class_a), seq=0)
            ScheduleTestSubject.objects.create(exp=req, subject=class_b,
                                               text=_token_text(class_b), seq=0)
            BooleanToken.objects.create(exp=req, text="NOT", seq=10)

            ScheduleConstraint.objects.create(
                program=program, condition=cond, requirement=req,
                on_failure=_on_failure,
            )

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
