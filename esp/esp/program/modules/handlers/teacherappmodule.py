"""
Teacher Application Module

This module provides functionality for managing teacher applications for programs.
It complements the Student Application System and allows programs to require
teachers to submit applications for their classes.
"""

from esp.program.modules.base import ProgramModuleObj, ProgramModule
from esp.program.models import TeacherApplication, TeacherAppQuestion, TeacherAppResponse, TeacherAppReview
from esp.users.models import ESPUser
from esp.web.util import render_to_response
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.db import transaction
from django import forms

class TeacherApplicationModule(ProgramModuleObj):
    """Teacher Application Module for managing teacher applications."""
    
    @classmethod
    def module_properties(cls):
        """Return module properties."""
        return {
            'admin_title': 'Teacher Applications',
            'link_title': 'Teacher Applications',
            'main_title': 'Teacher Applications',
            'module_url_name': 'teacherapp',
        }
    
    def isApplicable(self, user):
        """Check if this module is applicable for the user."""
        return user.isTeacher() or user.isAdministrator()
    
    def getLinks(self):
        """Get navigation links for this module."""
        links = []
        
        if self.user.isTeacher():
            links.append({
                'link': reverse('teacherapp_my_applications', args=[self.program.url]),
                'title': 'My Applications',
                'desc': 'View and manage your teacher applications'
            })
        
        if self.user.isAdministrator():
            links.append({
                'link': reverse('teacherapp_manage_questions', args=[self.program.url]),
                'title': 'Manage Questions',
                'desc': 'Create and edit application questions'
            })
            links.append({
                'link': reverse('teacherapp_review_applications', args=[self.program.url]),
                'title': 'Review Applications',
                'desc': 'Review and approve/reject teacher applications'
            })
        
        return links
    
    def teacherView(self, request, args, kwargs):
        """Main teacher view for applications."""
        if not self.user.isTeacher():
            raise Http404("You must be a teacher to access this page.")
        
        return HttpResponseRedirect(reverse('teacherapp_my_applications', args=[self.program.url]))
    
    def adminView(self, request, args, kwargs):
        """Main admin view for applications."""
        if not self.user.isAdministrator():
            raise Http404("You must be an administrator to access this page.")
        
        return HttpResponseRedirect(reverse('teacherapp_manage_questions', args=[self.program.url]))


@login_required
def my_applications(request, prog_url):
    """View teacher's own applications."""
    from esp.program.models import Program
    
    try:
        program = Program.objects.get(url=prog_url)
    except Program.DoesNotExist:
        raise Http404("Program not found.")
    
    if not request.user.isTeacher():
        raise Http404("You must be a teacher to access this page.")
    
    applications = TeacherApplication.objects.filter(
        user=request.user,
        subject__parent_program=program
    ).select_related('subject').order_by('-created')
    
    context = {
        'program': program,
        'applications': applications,
        'user': request.user,
    }
    
    return render_to_response('program/teacherapp/my_applications.html', request, context)


@login_required
def create_application(request, prog_url, subject_id):
    """Create a new teacher application for a subject."""
    from esp.program.models import ClassSubject
    
    try:
        program = Program.objects.get(url=prog_url)
        subject = ClassSubject.objects.get(id=subject_id, parent_program=program)
    except (Program.DoesNotExist, ClassSubject.DoesNotExist):
        raise Http404("Program or subject not found.")
    
    if not request.user.isTeacher():
        raise Http404("You must be a teacher to access this page.")
    
    # Check if application already exists
    existing_app = TeacherApplication.objects.filter(
        user=request.user,
        subject=subject
    ).first()
    
    if existing_app:
        return HttpResponseRedirect(reverse('teacherapp_edit_application', args=[prog_url, existing_app.id]))
    
    # Create new application
    application = TeacherApplication(
        user=request.user,
        program=program,
        subject=subject
    )
    
    if request.method == 'POST':
        forms = application.get_forms(request.POST)
        
        if all(form.is_valid() for form in forms):
            with transaction.atomic():
                for form in forms:
                    form.save()
                application.submit()
            
            return HttpResponseRedirect(reverse('teacherapp_my_applications', args=[prog_url]))
    else:
        forms = application.get_forms()
    
    context = {
        'program': program,
        'subject': subject,
        'application': application,
        'forms': forms,
        'user': request.user,
    }
    
    return render_to_response('program/teacherapp/create_application.html', request, context)


@login_required
def edit_application(request, prog_url, app_id):
    """Edit an existing teacher application."""
    from esp.program.models import Program
    
    try:
        program = Program.objects.get(url=prog_url)
        application = TeacherApplication.objects.get(
            id=app_id,
            user=request.user,
            program=program
        )
    except (Program.DoesNotExist, TeacherApplication.DoesNotExist):
        raise Http404("Application not found.")
    
    if application.submitted:
        raise Http404("Cannot edit submitted application.")
    
    if request.method == 'POST':
        forms = application.get_forms(request.POST)
        
        if all(form.is_valid() for form in forms):
            with transaction.atomic():
                for form in forms:
                    form.save()
                application.submit()
            
            return HttpResponseRedirect(reverse('teacherapp_my_applications', args=[prog_url]))
    else:
        forms = application.get_forms()
    
    context = {
        'program': program,
        'application': application,
        'subject': application.subject,
        'forms': forms,
        'user': request.user,
    }
    
    return render_to_response('program/teacherapp/edit_application.html', request, context)


@permission_required('program.admin', raise_exception=True)
def manage_questions(request, prog_url):
    """Manage application questions for administrators."""
    from esp.program.models import Program, ClassSubject
    
    try:
        program = Program.objects.get(url=prog_url)
    except Program.DoesNotExist:
        raise Http404("Program not found.")
    
    # Get program-level questions
    program_questions = TeacherAppQuestion.objects.filter(
        program=program,
        subject__isnull=True
    ).order_by('seq')
    
    # Get class-level questions
    class_questions = TeacherAppQuestion.objects.filter(
        subject__parent_program=program
    ).select_related('subject').order_by('subject__title', 'seq')
    
    subjects = ClassSubject.objects.filter(parent_program=program).order_by('title')
    
    context = {
        'program': program,
        'program_questions': program_questions,
        'class_questions': class_questions,
        'subjects': subjects,
    }
    
    return render_to_response('program/teacherapp/manage_questions.html', request, context)


@permission_required('program.admin', raise_exception=True)
def review_applications(request, prog_url):
    """Review and approve/reject teacher applications."""
    from esp.program.models import Program
    
    try:
        program = Program.objects.get(url=prog_url)
    except Program.DoesNotExist:
        raise Http404("Program not found.")
    
    applications = TeacherApplication.objects.filter(
        program=program,
        submitted=True,
        needs_review=True
    ).select_related('user', 'subject').order_by('-submitted_date')
    
    context = {
        'program': program,
        'applications': applications,
    }
    
    return render_to_response('program/teacherapp/review_applications.html', request, context)


@permission_required('program.admin', raise_exception=True)
def approve_application(request, prog_url, app_id):
    """Approve a teacher application."""
    from esp.program.models import Program
    
    try:
        program = Program.objects.get(url=prog_url)
        application = TeacherApplication.objects.get(
            id=app_id,
            program=program
        )
    except (Program.DoesNotExist, TeacherApplication.DoesNotExist):
        raise Http404("Application not found.")
    
    application.approve()
    
    return HttpResponseRedirect(reverse('teacherapp_review_applications', args=[prog_url]))


@permission_required('program.admin', raise_exception=True)
def reject_application(request, prog_url, app_id):
    """Reject a teacher application."""
    from esp.program.models import Program
    
    try:
        program = Program.objects.get(url=prog_url)
        application = TeacherApplication.objects.get(
            id=app_id,
            program=program
        )
    except (Program.DoesNotExist, TeacherApplication.DoesNotExist):
        raise Http404("Application not found.")
    
    application.reject()
    
    return HttpResponseRedirect(reverse('teacherapp_review_applications', args=[prog_url]))


# Register the module
module = ProgramModule(TeacherApplicationModule, 'TeacherApplicationModule')
