from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, aux_call
from esp.utils.web import render_to_response
from esp.dbmail.models import MessageRequest, PlainRedirect, ActionHandler
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, PersistentQueryFilter
from django.conf import settings
from django.template.loader import render_to_string
from django.template import Template, Context as DjangoContext
from django.db.models import Q
import re

class TeacherCommModule(ProgramModuleObj):
    doc = """Communicate with students in your own classes."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Communications Panel for Teachers",
            "link_title": "Email Your Students",
            "module_type": "teach",
            "seq": 20,
            "choosable": 1,
        }

    @main_call
    @needs_teacher
    def commpanel(self, request, tl, one, two, module, extra, prog):
        # Get all sections taught by this teacher
        from esp.program.models import ClassSection
        sections = ClassSection.objects.filter(parent_class__teachers=request.user, parent_class__parent_program=prog)
        
        context = {
            'sections': sections,
            'program': prog,
        }
        return render_to_response(self.baseDir() + 'commpanel_teacher.html', request, context)

    @aux_call
    @needs_teacher
    def commprev(self, request, tl, one, two, module, extra, prog):
        from esp.program.models import ClassSection
        section_ids = request.POST.getlist('section_ids')
        subject = request.POST.get('subject', '')
        body = request.POST.get('body', '')
        template = request.POST.get('template', 'default')

        # Filter students in those sections
        sections = ClassSection.objects.filter(id__in=section_ids, parent_class__teachers=request.user)
        students = ESPUser.objects.filter(studentregistration__section__in=sections, studentregistration__relationship__name='Enrolled').distinct()
        
        listcount = students.count()
        if listcount == 0:
            return render_to_response(self.baseDir() + 'no_recipients.html', request, {'program': prog})

        # Render preview for the first student
        firstuser = students[0]
        rendered_text = render_to_string('email/{}_email.html'.format(template), {'msgbody': body})
        contextdict = {
            'user': ActionHandler(firstuser, firstuser),
            'program': ActionHandler(prog, firstuser),
            'request': ActionHandler(MessageRequest(), firstuser),
            'EMAIL_HOST_SENDER': settings.EMAIL_HOST_SENDER
        }
        preview_text = Template(rendered_text).render(DjangoContext(contextdict))

        context = {
            'section_ids': ",".join(section_ids),
            'listcount': listcount,
            'subject': subject,
            'body': body,
            'template': template,
            'rendered_text': preview_text,
            'program': prog,
        }
        return render_to_response(self.baseDir() + 'preview_teacher.html', request, context)

    @aux_call
    @needs_teacher
    def commfinal(self, request, tl, one, two, module, extra, prog):
        from esp.program.models import ClassSection
        section_ids = request.POST.get('section_ids', '').split(',')
        subject = request.POST.get('subject', '')
        body = request.POST.get('body', '')
        template = request.POST.get('template', 'default')

        sections = ClassSection.objects.filter(id__in=section_ids, parent_class__teachers=request.user)
        students = ESPUser.objects.filter(studentregistration__section__in=sections, studentregistration__relationship__name='Enrolled').distinct()
        
        # We need a PersistentQueryFilter for the MessageRequest
        filter_q = Q(studentregistration__section__in=sections, studentregistration__relationship__name='Enrolled')
        filter_obj = PersistentQueryFilter.create_from_Q(ESPUser, filter_q)

        fromemail = '%s <%s@%s>' % (Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME),
                                    "info", settings.SITE_INFO[1])

        rendered_text = render_to_string('email/{}_email.html'.format(template), {'msgbody': body})

        MessageRequest.createRequest(
            var_dict={'user': request.user, 'program': prog},
            subject=subject,
            recipients=filter_obj,
            sendto_fn_name=MessageRequest.SEND_TO_SELF_REAL,
            sender=fromemail,
            creator=request.user,
            msgtext=rendered_text,
            public=False,
            special_headers_dict={'Reply-To': request.user.email}
        ).save()

        return render_to_response(self.baseDir() + 'finished.html', request, {'program': prog})

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
