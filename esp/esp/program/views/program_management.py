import json
from django.http import HttpResponseRedirect
from django.forms.models import model_to_dict
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from esp.utils.web import render_to_response
from esp.program.models import Program, ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.program.forms import ProgramCreationForm
from esp.program.setup import prepare_program, commit_program
from esp.users.models import admin_required, Permission
from esp.accounting.controllers import ProgramAccountingController
from esp.resources.models import ResourceType
from esp.tagdict.models import Tag
from esp.mailman import create_list, load_list_settings, apply_list_settings, add_list_members

@admin_required
def manage_programs(request):
    #as admin required implies can administrate all programs now,
    admPrograms = Program.objects.all().order_by('-id')
    context = {'admPrograms': admPrograms,
               'user': request.user}
    return render_to_response('program/manage_programs.html', request, context)

@admin_required
def newprogram(request):
    # First, if the user selected a template program, pre-populate fields with that program's data.
    template_prog = None
    template_prog_id = None
    if 'template_prog' in request.GET and (int(request.GET["template_prog"])) != 0:  # user might select `None` whose value is 0, we need to check for 0.
        template_prog_id = int(request.GET["template_prog"])
        tprogram = Program.objects.get(id=template_prog_id)
        request.session['template_prog'] = template_prog_id
        template_prog = {}
        template_prog.update(model_to_dict(tprogram))
        del template_prog["id"]
        template_prog["program_type"] = tprogram.program_type
        '''
        As Program Name should be new for each new program created then it is better to not to show old program names in input box .
        template_prog["term"] = tprogram.program_instance()
        template_prog["term_friendly"] = tprogram.niceName()
        '''

        student_reg_bits = list(Permission.objects.filter(permission_type__startswith='Student', program=template_prog_id).order_by('-start_date'))
        if len(student_reg_bits) > 0:
            newest_bit = student_reg_bits[0]
            oldest_bit = student_reg_bits[-1]

            template_prog["student_reg_start"] = oldest_bit.start_date
            template_prog["student_reg_end"] = newest_bit.end_date

        teacher_reg_bits = list(Permission.objects.filter(permission_type__startswith='Teacher', program=template_prog_id).order_by('-start_date'))
        if len(teacher_reg_bits) > 0:
            newest_bit = teacher_reg_bits[0]
            oldest_bit = teacher_reg_bits[-1]

            template_prog["teacher_reg_start"] = oldest_bit.start_date
            template_prog["teacher_reg_end"] = newest_bit.end_date

        pac = ProgramAccountingController(tprogram)
        line_items = pac.get_lineitemtypes(required_only=True).filter(text="Program admission").values('amount_dec')

        template_prog["base_cost"] = int(sum(x["amount_dec"] for x in line_items))
        template_prog["sibling_discount"] = tprogram.sibling_discount

    # If the form has been submitted, process it.
    if request.method == 'POST':
        form = ProgramCreationForm(request.POST)
        if form.is_valid():
            temp_prog = form.save(commit=False)
            perms, modules = prepare_program(temp_prog, form.cleaned_data)
            new_prog = form.save(commit = True)
            commit_program(new_prog, perms, form.cleaned_data['base_cost'], form.cleaned_data['sibling_discount'])
            # Create the default resource types now
            default_restypes = Tag.getTag('default_restypes')
            if default_restypes:
                resource_type_labels = json.loads(default_restypes)
                resource_types = [ResourceType.get_or_create(x, new_prog) for x in resource_type_labels]
            # If a template program was chosen, load modules based on that program's
            if template_prog is not None:
                # Force all ProgramModuleObjs and their extensions to be created now
                old_prog = Program.objects.get(id=template_prog_id)
                # If we are using another program as a template, let's copy the seq and required values from that program.
                new_prog.getModules(old_prog=old_prog)
                # Copy CRMI settings from old program
                old_crmi = ClassRegModuleInfo.objects.get(program=old_prog)
                new_crmi = ClassRegModuleInfo.objects.get(program=new_prog)
                for field in old_crmi._meta.fields:
                    if field.name not in ["id", "program"]:
                        setattr(new_crmi, field.name, getattr(old_crmi, field.name))
                new_crmi.save()
                # Copy SCRMI settings from old program
                old_scrmi = StudentClassRegModuleInfo.objects.get(program=old_prog)
                new_scrmi = StudentClassRegModuleInfo.objects.get(program=new_prog)
                for field in old_scrmi._meta.fields:
                    if field.name not in ["id", "program"]:
                        setattr(new_scrmi, field.name, getattr(old_scrmi, field.name))
                new_scrmi.save()
                # Copy tags from old program
                ct = ContentType.objects.get_for_model(old_prog)
                old_tags = Tag.objects.filter(content_type=ct, object_id=old_prog.id)
                for old_tag in old_tags:
                    # Some tags we don't want to import
                    if old_tag.key not in ['learn_extraform_id', 'teach_extraform_id', 'quiz_form_id', 'student_lottery_run']:
                        new_tag, created = Tag.objects.get_or_create(key=old_tag.key, content_type=ct, object_id=new_prog.id)
                        # Some tags get created during program creation (e.g. sibling discount), and we don't want to override those
                        if created:
                            new_tag.value = old_tag.value
                            new_tag.save()
            # If no template program is selected, create new modules
            else:
                # Create new modules
                new_prog.getModules()
            manage_url = '/manage/' + new_prog.url + '/resources'
            # While we're at it, create the program's mailing list
            if settings.USE_MAILMAN and 'mailman_moderator' in list(settings.DEFAULT_EMAIL_ADDRESSES.keys()):
                mailing_list_name = "%s_%s" % (new_prog.program_type, new_prog.program_instance)
                teachers_list_name = "%s-%s" % (mailing_list_name, "teachers")
                students_list_name = "%s-%s" % (mailing_list_name, "students")

                create_list(students_list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])
                create_list(teachers_list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])

                load_list_settings(teachers_list_name, "lists/program_mailman.config")
                load_list_settings(students_list_name, "lists/program_mailman.config")

                apply_list_settings(teachers_list_name, {'owner': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], new_prog.director_email]})
                apply_list_settings(students_list_name, {'owner': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], new_prog.director_email]})

                if 'archive' in list(settings.DEFAULT_EMAIL_ADDRESSES.keys()):
                    add_list_members(students_list_name, [new_prog.director_email, settings.DEFAULT_EMAIL_ADDRESSES['archive']])
                    add_list_members(teachers_list_name, [new_prog.director_email, settings.DEFAULT_EMAIL_ADDRESSES['archive']])
            # Submit and create the program
            return HttpResponseRedirect(manage_url)
    # If the form has not been submitted, the default view is a blank form (or the pre-populated form with the template data).
    else:
        if template_prog:
            form = ProgramCreationForm(template_prog)
        else:
            form = ProgramCreationForm()

    return render_to_response('program/newprogram.html', request, {'form': form, 'programs': Program.objects.all().order_by('-id'), 'template_prog_id': template_prog_id})
