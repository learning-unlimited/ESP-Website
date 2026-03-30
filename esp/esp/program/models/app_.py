__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

from esp.db.fields import AjaxForeignKey
from esp.users.models import ESPUser

from django.db import models
from django import forms
from django.utils.deconstruct import deconstructible

import datetime

__all__ = ['StudentAppQuestion', 'StudentAppResponse', 'StudentAppReview', 'StudentApplication', 'TeacherAppQuestion', 'TeacherAppResponse', 'TeacherAppReview', 'TeacherApplication']

@deconstructible
class BaseAppElement(object):
    """ Base class for models that you would like to generate forms from.
    Make this a subclass of the model and overload the two attributes:
    -   _element_name: a slug-like name for the model to differentiate its
        form elements from other models
    -   _field_names: the names of the fields you would like to show up
        on the forms
    Call get_form (optionally passing in a dictionary of initial data) to
    get a form object from an instance of your model.  Call update (passing
    in a form that you got from get_form) to save the data from the form
    to the instance.        """
    _element_name = ''
    _field_names = []

    def get_form(self, *args, **kwargs):
        def get_field_by_name(name):
            for f in self._meta.fields:
                if f.name == name:
                    return f
            return None

        #   Avoid setting the prefix if the instance has not been saved to the
        #   database.  This may be necessary in order to generate forms without
        #   saving instances until the form is submitted.  The view function
        #   should set the prefix appropriately after calling get_form in this
        #   case.
        if 'form_prefix' in kwargs:
            form_prefix = kwargs['form_prefix']
            del kwargs['form_prefix']
        else:
            if hasattr(self, 'id') and self.id:
                form_prefix = f'{self._element_name}_{self.id}'
            else:
                form_prefix = 'TEMP'

        class form_class(forms.ModelForm):
            class Meta:
                fields = "__all__"
                model = self.__class__

        #   Enlarge text fields to a reasonable size (dangit Django).
        for field in self._field_names:
            django_field = get_field_by_name(field)
            if isinstance(django_field, models.TextField):
                form_class.base_fields[field].widget = forms.Textarea(attrs={'cols': 80, 'rows': 8})
                form_class.base_fields[field].required = False

        if len(args) > 0:
            initial_dict = args[0].copy()
            populating_from_form = (initial_dict != {})
            args = args[1:]
        else:
            initial_dict = {}
            populating_from_form = False

        #   Don't overwrite existing data supplied as an argument.
        #   BooleanFields are weird; if un-set, they're simply not given in the POST dictionary.
        if not populating_from_form:
            for field_name in self._field_names:
                initial_dict[form_prefix + '-' + field_name] = getattr(self, field_name)

        form = form_class(initial_dict, prefix=form_prefix, *args, **kwargs)
        form.target = self
        return form

    def update(self, form):
        self.date = datetime.datetime.now()
        for field_name in self._field_names:
            if field_name in form.cleaned_data:
                setattr(self, field_name, form.cleaned_data[field_name])
        self.save()

class StudentAppQuestion(BaseAppElement, models.Model):
    """ A question for a student application form, a la Junction or Delve.
    Questions pertaining to the program or to classes the student has
    applied to will appear on their application. """
    from esp.program.models import Program, ClassSubject

    _element_name = 'question'
    _field_names = ['question', 'directions']

    program = models.ForeignKey(Program, blank=True, null=True, editable = False, on_delete=models.CASCADE)
    subject = models.ForeignKey(ClassSubject, blank=True, null=True, editable = False, on_delete=models.CASCADE)
    question = models.TextField(help_text='The prompt that your students will see.')
    directions = models.TextField(help_text='Specify any additional notes (such as the length of response you desire) here.', blank=True, null=True)

    def __str__(self):
        if self.subject is not None:
            return f'{self.question[:80]} ({self.subject.title})'
        else:
            return f'{self.question[:80]} ({self.program.niceName()})'

    class Meta:
        app_label = 'program'
        db_table = 'program_studentappquestion'

class StudentAppResponse(BaseAppElement, models.Model):
    """ A response to an application question. """
    question = models.ForeignKey(StudentAppQuestion, editable=False, on_delete=models.CASCADE)
    response = models.TextField(default='')
    complete = models.BooleanField(default=False, help_text='Please check this box when you are finished responding to this question.')

    _element_name = 'response'
    _field_names = ['response', 'complete']

    def __str__(self):
        return f'Response to {self.question.question}: {self.response[:80]}...'

    class Meta:
        app_label = 'program'
        db_table = 'program_studentappresponse'

class StudentAppReview(BaseAppElement, models.Model):
    """ An individual review for a student application question.
    The application can be reviewed by any director of the program or
    teacher of a class for which the student applied. """

    reviewer = AjaxForeignKey(ESPUser, editable=False, on_delete=models.CASCADE)
    date = models.DateTimeField(default=datetime.datetime.now, editable=False)
    score = models.PositiveIntegerField(null=True, blank=True, help_text='Please rate each student', choices=((10, "Yes"), (5, "Maybe"), (1, "No")))
    comments = models.TextField()
    reject = models.BooleanField(default=False, editable=False)

    _element_name = 'review'
    _field_names = ['score', 'comments', 'reject']

    def __str__(self):
        return f'{self.score} by {self.reviewer.username}: {self.comments[:80]}...'

    class Meta:
        app_label = 'program'
        db_table = 'program_studentappreview'

class StudentApplication(models.Model):
    """ Student applications for Junction and any other programs that need them. """
    from esp.program.models import Program

    program = models.ForeignKey(Program, editable=False, on_delete=models.CASCADE)
    user    = AjaxForeignKey(ESPUser, editable=False, on_delete=models.CASCADE)

    questions = models.ManyToManyField(StudentAppQuestion)
    responses = models.ManyToManyField(StudentAppResponse)
    reviews = models.ManyToManyField(StudentAppReview)

    done = models.BooleanField(default=False, editable = False)

    #   Legacy fields
    teacher_score = models.PositiveIntegerField(editable=False, null=True, blank=True)
    director_score = models.PositiveIntegerField(editable=False, null=True, blank=True)
    rejected       = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return str(self.user)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save()
        self.set_questions()

    def set_questions(self):
        new_user = self.user
        existing_list = self.questions.all().values_list('id', flat=True)
        new_list = list(StudentAppQuestion.objects.filter(program=self.program).values_list('id', flat=True))
        new_list += list(StudentAppQuestion.objects.filter(subject__in=new_user.getAppliedClasses(self.program)).values_list('id', flat=True))

        to_remove = [e for e in existing_list if (e not in new_list)]
        for i in to_remove:
            self.questions.remove(i)
        to_add = [e for e in new_list if (e not in existing_list)]
        for i in to_add:
            self.questions.add(i)

    def get_forms(self, data={}):
        """ Get a list of forms for the student to fill out.
        This function sets a target attribute on each form so that
        the update function can be called directly on target. """

        #   Get forms for already existing responses.
        forms = []
        new_user = self.user
        applied_classes = new_user.getAppliedClasses(self.program)
        for r in self.responses.filter(question__subject__in=applied_classes):
            f = r.get_form(data)
            f.target = r
            forms.append(f)

        #   Create responses if necessary for the other questions, and get their forms.
        for q in self.questions.all():
            if self.responses.filter(question=q).count() == 0:
                r = StudentAppResponse(question=q)
                r.save()
                self.responses.add(r)
                f = r.get_form(data)
                forms.append(f)

        return forms

    def update(self, form):
        """ Use this if you're not sure what response the form is relevant to. """
        for r in self.responses.all():
            r.update(form)

    class Meta:
        app_label = 'program'
        db_table = 'program_junctionstudentapp'


class TeacherAppQuestion(StudentAppQuestion):
    """ Teacher application questions for programs that need them. """
    from esp.program.models import Program, ClassSubject
    
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    subject = models.ForeignKey(ClassSubject, null=True, blank=True, on_delete=models.CASCADE)
    
    def __str__(self):
        if self.subject:
            return f"{self.program.name} - {self.subject.title} - {self.prompt}"
        else:
            return f"{self.program.name} - {self.prompt}"
    
    class Meta:
        app_label = 'program'
        db_table = 'program_teacherappquestion'


class TeacherAppResponse(StudentAppResponse):
    """ Teacher application responses. """
    question = models.ForeignKey(TeacherAppQuestion, on_delete=models.CASCADE)
    
    class Meta:
        app_label = 'program'
        db_table = 'program_teacherappresponse'


class TeacherAppReview(StudentAppReview):
    """ Teacher application reviews. """
    from esp.users.models import ESPUser
    response = models.ForeignKey(TeacherAppResponse, on_delete=models.CASCADE)
    reviewer = AjaxForeignKey(ESPUser, on_delete=models.CASCADE)
    
    class Meta:
        app_label = 'program'
        db_table = 'program_teacherappreview'


class TeacherApplication(models.Model):
    """ Teacher applications for programs that need them. """
    from esp.program.models import Program, ClassSubject

    program = models.ForeignKey(Program, editable=False, on_delete=models.CASCADE)
    user = AjaxForeignKey(ESPUser, editable=False, on_delete=models.CASCADE)
    subject = models.ForeignKey(ClassSubject, editable=False, on_delete=models.CASCADE)

    questions = models.ManyToManyField(TeacherAppQuestion)
    responses = models.ManyToManyField(TeacherAppResponse)
    reviews = models.ManyToManyField(TeacherAppReview)

    done = models.BooleanField(default=False, editable=False)
    submitted = models.BooleanField(default=False, editable=False)
    
    # Application status
    approved = models.BooleanField(default=False, editable=False)
    rejected = models.BooleanField(default=False, editable=False)
    needs_review = models.BooleanField(default=True, editable=False)
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True, editable=False)
    updated = models.DateTimeField(auto_now=True, editable=False)
    submitted_date = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return f"{self.user} - {self.subject.title} application"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save()
        self.set_questions()

    def set_questions(self):
        """ Set questions for this application based on program and subject. """
        existing_list = self.questions.all().values_list('id', flat=True)
        new_list = list(TeacherAppQuestion.objects.filter(program=self.program).values_list('id', flat=True))
        new_list += list(TeacherAppQuestion.objects.filter(subject=self.subject).values_list('id', flat=True))

        to_remove = [e for e in existing_list if (e not in new_list)]
        for i in to_remove:
            self.questions.remove(i)
        to_add = [e for e in new_list if (e not in existing_list)]
        for i in to_add:
            self.questions.add(i)

    def get_forms(self, data={}):
        """ Get a list of forms for the teacher to fill out. """
        forms = []
        
        # Get forms for already existing responses
        for r in self.responses.filter(question__subject=self.subject):
            f = r.get_form(data)
            if f is not None:
                f.target = r
                forms.append(f)

        # Get forms for questions that don't have responses yet
        for q in self.questions.filter(subject=self.subject):
            if not self.responses.filter(question=q).exists():
                f = q.get_form(data)
                if f is not None:
                    f.target = TeacherAppResponse(question=q, user=self.user)
                    forms.append(f)

        return forms

    def update(self, form):
        """ Use this if you're not sure what response the form is relevant to. """
        for r in self.responses.all():
            r.update(form)

    def submit(self):
        """ Submit the application for review. """
        self.done = True
        self.submitted = True
        self.submitted_date = datetime.datetime.now()
        self.save()

    def approve(self):
        """ Approve the application. """
        self.approved = True
        self.rejected = False
        self.needs_review = False
        self.save()

    def reject(self):
        """ Reject the application. """
        self.approved = False
        self.rejected = True
        self.needs_review = False
        self.save()

    class Meta:
        app_label = 'program'
        db_table = 'program_teacherapplication'
        indexes = [
            models.Index(fields=['program', 'subject'], name='teacherapp_prog_subj_idx'),
            models.Index(fields=['user', 'subject'], name='teacherapp_user_subj_idx'),
            models.Index(fields=['submitted'], name='teacherapp_submitted_idx'),
            models.Index(fields=['needs_review'], name='teacherapp_review_idx'),
        ]

