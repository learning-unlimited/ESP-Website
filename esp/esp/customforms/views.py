from copy import deepcopy
import json
from tkinter.tix import Form

from django.db import transaction
from django.shortcuts import redirect
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.db import connection
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import user_passes_test, login_required

from esp.customforms.models import Form
from esp.customforms.models import Page, Section, Field, Attribute
from esp.program.models import Program
from esp.customforms.DynamicModel import DynamicModelHandler as DMH
from esp.customforms.DynamicForm import FormHandler
from esp.customforms.linkfields import cf_cache
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.middleware import ESPError
from esp.utils.web import render_to_response, zip_download




def _check_form_permission(request, form):
    if request.user.isAdministrator():
        return
    if form.created_by == request.user:
        return
    raise PermissionDenied(
        "You do not have permission to access this form's data."
    )


def test_func(user):
    return user.is_authenticated and (
        user.is_morphed() or user.isTeacher() or user.isAdministrator()
    )




@login_required
def viewResponse(request, form_id):
    if not (request.user.isTeacher() or request.user.isAdministrator()):
        return HttpResponseRedirect('/')
    try:
        form_id = int(form_id)
    except ValueError:
        raise Http404
    form = get_object_or_404(Form, pk=form_id)
    _check_form_permission(request, form)
    return render_to_response('customforms/view_results.html', request, {'form': form})


@user_passes_test(test_func)
def getExcelData(request, form_id):
    try:
        form_id = int(form_id)
    except ValueError:
        return HttpResponse(status=400)
    form = get_object_or_404(Form, pk=form_id)
    _check_form_permission(request, form)
    fh = FormHandler(form=form, request=request)
    wbk = fh.getResponseExcel()
    response = HttpResponse(
        wbk.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename=%s.xlsx' % form.title
    return response


@user_passes_test(test_func)
def getData(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            try:
                form_id = int(request.GET['form_id'])
            except (ValueError, KeyError):
                return HttpResponse(status=400)
            form = get_object_or_404(Form, pk=form_id)
            _check_form_permission(request, form)
            fh = FormHandler(form=form, request=request)
            resp_data = json.dumps(fh.getResponseData(form), cls=DjangoJSONEncoder)
            return HttpResponse(resp_data)
    return HttpResponse(status=400)


@user_passes_test(test_func)
def bulkDownloadFiles(request):
    if request.method == 'GET':
        try:
            form_id = int(request.GET['form_id'])
            question_name = request.GET['question_name']
        except (ValueError, KeyError):
            return HttpResponse(status=400)
        form = get_object_or_404(Form, pk=form_id)
        _check_form_permission(request, form)
        dmh = DMH(form=form)
        dyn = dmh.createDynModel()
        filenames = [resp[question_name] for resp in dyn.objects.all().values()]
        return zip_download(filenames, 'surveyfiles')
    return HttpResponse(status=400)




@user_passes_test(test_func)
def landing(request):
    forms = Form.objects.all().order_by('-link_type', '-link_id', '-id')
    if not (request.user.isAdministrator() or request.user.is_morphed()):
        forms = forms.filter(created_by=request.user)
    for form in forms:
        if form.link_type in list(cf_cache.only_fkey_models.keys()):
            if form.link_id == -1:
                form.link_obj = "User's choice"
            else:
                form.link_obj = cf_cache.only_fkey_models[form.link_type].objects.get(id=form.link_id)
    return render_to_response("customforms/landing.html", request, {'form_list': forms})


@user_passes_test(test_func)
def formBuilder(request):
    prog_list = Program.objects.all()
    form_list = Form.objects.all().order_by('-id')
    if not (request.user.isAdministrator() or request.user.is_morphed()):
        form_list = form_list.filter(created_by=request.user)
    context = {
        'prog_list': prog_list,
        'form_list': form_list,
        'only_fkey_models': list(cf_cache.only_fkey_models.keys()),
    }
    if 'edit' in request.GET and request.GET.get('edit'):
        context['edit'] = request.GET.get('edit')
    return render_to_response('customforms/index.html', request, context)


@user_passes_test(test_func)
def formBuilderData(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            data = {}
            data['only_fkey_models'] = list(cf_cache.only_fkey_models.keys())
            data['link_fields'] = {}
            for category, category_info in cf_cache.link_fields.items():
                data['link_fields'][category] = {}
                data['link_fields'][category].update(category_info['fields'])
            return HttpResponse(json.dumps(data))
    return HttpResponse(status=400)


def getPerms(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            try:
                prog_id = int(request.GET['prog_id'])
            except ValueError:
                return HttpResponse(status=400)
            prog = Program.objects.get(pk=prog_id)
            perms = {'teachers': [], 'students': []}
            for module in prog.getModules(None):
                teach_desc = module.teacherDesc()
                stud_desc = module.studentDesc()
                if teach_desc:
                    for k, v in teach_desc.items():
                        perms['teachers'].append([k, v])
                elif stud_desc:
                    for k, v in stud_desc.items():
                        perms['students'].append([k, v])
            return HttpResponse(json.dumps(perms))
    return HttpResponse(status=400)


@user_passes_test(test_func)
@transaction.atomic
def onSubmit(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'POST':
            try:
                metadata = json.loads(request.body)
                fields = []

                title = metadata['title'][0:Form._meta.get_field('title').max_length]
                link_type = metadata['link_type'][0:Form._meta.get_field('link_type').max_length]
                perms = metadata['perms'][0:Form._meta.get_field('perms').max_length]
                success_message = metadata['success_message'][0:Form._meta.get_field('success_message').max_length]
                success_url = metadata['success_url'][0:Form._meta.get_field('success_url').max_length]

                form = Form.objects.create(
                    title=title,
                    description=metadata['desc'],
                    created_by=request.user,
                    link_type=link_type,
                    link_id=int(metadata['link_id']),
                    anonymous=metadata['anonymous'],
                    perms=perms,
                    success_message=success_message,
                    success_url=success_url,
                )

                if 'link_module' in metadata:
                    try:
                        prog = Program.objects.get(id=metadata['link_id'])
                    except Program.DoesNotExist:
                        return ESPError('No program with ID %i' % (metadata['link_id']))
                    if not prog.hasModule(metadata['link_module']):
                        return ESPError('Program does not have %s enabled' % (metadata['link_module']))
                    if metadata['link_module'] == 'StudentCustomFormModule':
                        Tag.setTag(key='learn_extraform_id', value=form.id, target=prog)
                    elif metadata['link_module'] == 'TeacherCustomFormModule':
                        Tag.setTag(key='teach_extraform_id', value=form.id, target=prog)
                    elif metadata['link_module'] == 'TeacherQuizModule':
                        Tag.setTag(key='quiz_form_id', value=form.id, target=prog)
                    else:
                        return ESPError('Module %s does not use a custom form or is not implemented' % (metadata['link_module']))

                for page in metadata['pages']:
                    new_page = Page.objects.create(form=form, seq=int(page['seq']))
                    for section in page['sections']:
                        new_section = Section.objects.create(
                            page=new_page,
                            title=section['data']['question_text'],
                            description=section['data']['help_text'],
                            seq=int(section['data']['seq']),
                        )
                        for field in section['fields']:
                            new_field = Field.objects.create(
                                form=form,
                                section=new_section,
                                field_type=field['data']['field_type'],
                                seq=int(field['data']['seq']),
                                label=field['data']['question_text'],
                                help_text=field['data']['help_text'],
                                required=field['data']['required'],
                            )
                            fields.append((new_field.id, new_field.field_type))
                            for atype, aval in field['data']['attrs'].items():
                                Attribute.objects.create(field=new_field, attr_type=atype, value=aval)

                dynH = DMH(form=form, fields=fields)
                dynH.createTable()
                return HttpResponse('OK')
            except Exception as err:
                return JsonResponse({'message': str(err)}, status=400)


def get_or_create_altered_obj(model, initial_id, **attrs):
    if model.objects.filter(id=initial_id).exists():
        obj = model.objects.get(id=initial_id)
        old_obj = deepcopy(obj)
        obj.__dict__.update(attrs)
        obj.save()
        created = False
    else:
        obj = model.objects.create(**attrs)
        old_obj = None
        created = True
    return (obj, old_obj, created)


def get_new_or_altered_obj(*args, **kwargs):
    return get_or_create_altered_obj(*args, **kwargs)[0]


@user_passes_test(test_func)
@transaction.atomic
def onModify(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'POST':
            try:
                metadata = json.loads(request.body)
                try:
                    form = Form.objects.get(id=int(metadata['form_id']))
                except (Form.DoesNotExist, ValueError):
                    raise ESPError('Form %s not found' % metadata['form_id'], log=False)
                dmh = DMH(form=form)
                link_models_list = []
                dmh._getModelFieldList()

                form.__dict__.update(
                    title=metadata['title'],
                    description=metadata['desc'],
                    perms=metadata['perms'],
                    success_message=metadata['success_message'],
                    success_url=metadata['success_url'],
                )
                form.save()

                Tag.objects.filter(
                    value=form.id,
                    key__in=['learn_extraform_id', 'teach_extraform_id', 'quiz_form_id'],
                ).delete()

                if 'link_module' in metadata:
                    try:
                        prog = Program.objects.get(id=metadata['link_id'])
                    except Program.DoesNotExist:
                        return ESPError('No program with ID %i' % (metadata['link_id']))
                    if not prog.hasModule(metadata['link_module']):
                        return ESPError('Program does not have %s enabled' % (metadata['link_module']))
                    if metadata['link_module'] == 'StudentCustomFormModule':
                        Tag.setTag(key='learn_extraform_id', value=form.id, target=prog)
                    elif metadata['link_module'] == 'TeacherCustomFormModule':
                        Tag.setTag(key='teach_extraform_id', value=form.id, target=prog)
                    elif metadata['link_module'] == 'TeacherQuizModule':
                        Tag.setTag(key='quiz_form_id', value=form.id, target=prog)
                    else:
                        return ESPError('Module %s does not use a custom form or is not implemented' % (metadata['link_module']))

                if form.link_type != metadata['link_type'] or form.link_id != metadata['link_id']:
                    dmh.change_only_fkey(form, form.link_type, metadata['link_type'], metadata['link_id'])

                curr_keys = {'pages': [], 'sections': [], 'fields': []}
                old_pages = Page.objects.filter(form=form)
                old_sections = Section.objects.filter(page__in=old_pages)
                old_fields = Field.objects.filter(form=form)

                for page in metadata['pages']:
                    curr_page = get_new_or_altered_obj(Page, page['parent_id'], form=form, seq=int(page['seq']))
                    curr_keys['pages'].append(curr_page.id)
                    for section in page['sections']:
                        curr_sect = get_new_or_altered_obj(
                            Section, section['data']['parent_id'],
                            page=curr_page,
                            title=section['data']['question_text'],
                            description=section['data']['help_text'],
                            seq=int(section['data']['seq']),
                        )
                        curr_keys['sections'].append(curr_sect.id)
                        for field in section['fields']:
                            (curr_field, old_field, field_created) = get_or_create_altered_obj(
                                Field, field['data']['parent_id'],
                                form=form, section=curr_sect,
                                field_type=field['data']['field_type'],
                                seq=int(field['data']['seq']),
                                label=field['data']['question_text'],
                                help_text=field['data']['help_text'],
                                required=field['data']['required'],
                            )
                            if field_created:
                                if cf_cache.isLinkField(curr_field.field_type):
                                    dmh.addLinkFieldColumn(curr_field)
                                else:
                                    dmh.addField(curr_field)
                            elif not cf_cache.isLinkField(curr_field.field_type):
                                dmh.updateField(curr_field, old_field)

                            if cf_cache.isLinkField(curr_field.field_type):
                                model_cls = cf_cache.modelForLinkField(curr_field.field_type)
                                if model_cls.__name__ not in link_models_list:
                                    link_models_list.append(model_cls.__name__)

                            for atype, aval in field['data']['attrs'].items():
                                curr_field.set_attribute(atype, aval)
                            curr_field.clean_attributes(list(field['data']['attrs'].keys()))
                            curr_keys['fields'].append(curr_field.id)

                del_fields = old_fields.exclude(id__in=curr_keys['fields'])
                for df in del_fields:
                    if cf_cache.isLinkField(df.field_type):
                        model_cls = cf_cache.modelForLinkField(df.field_type)
                        if model_cls.__name__ not in link_models_list:
                            dmh.removeLinkField(df)
                    else:
                        dmh.removeField(df)
                del_fields.delete()

                old_sections.exclude(id__in=curr_keys['sections']).delete()
                old_pages.exclude(id__in=curr_keys['pages']).delete()

                return HttpResponse('OK')
            except Exception as err:
                return JsonResponse({'message': str(err)}, status=400)


def hasPerm(user, form):
    if (not form.anonymous or form.perms != "") and not user.is_authenticated:
        return False, "You need to be logged in to view this form."
    if form.perms == "":
        return True, ""
    else:
        perms_list = form.perms.strip(',').split(',')
        main_perm = perms_list[0]
        prog_id = ""
        sub_perms = None
        if len(perms_list) > 1:
            prog_id = perms_list[1]
            if len(perms_list) > 2:
                sub_perms = perms_list[2:]
        Qlist = []
        Qlist.append(ESPUser.getAllOfType(main_perm))
        if sub_perms:
            if prog_id != "":
                prog = Program.objects.get(pk=int(prog_id))
                all_Qs = prog.getLists(QObjects=True)
                for perm in sub_perms:
                    Qlist.append(all_Qs[perm]['list'])
        if ESPUser.objects.filter(id=user.id).filter(*Qlist).exists():
            return True, ""
        else:
            return False, "You are not permitted to view this form."


def viewForm(request, form_id):
    try:
        form_id = int(form_id)
        form = Form.objects.get(pk=form_id)
    except (ValueError, Form.DoesNotExist):
        raise Http404
    perm, error_text = hasPerm(request.user, form)
    if not perm:
        return render_to_response('customforms/error.html', request, {'error_text': error_text})
    fh = FormHandler(form=form, request=request, user=request.user)
    return fh.get_wizard_view()


def success(request, form_id):
    try:
        form_id = int(form_id)
    except ValueError:
        raise Http404
    form = Form.objects.get(pk=form_id)
    return render_to_response('customforms/success.html', request, {
        'success_message': form.success_message,
        'success_url': form.success_url,
    })


@user_passes_test(test_func)
def getRebuildData(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            try:
                form_id = int(request.GET['form_id'])
            except ValueError:
                return HttpResponse(status=400)
            form = Form.objects.get(pk=form_id)
            fh = FormHandler(form=form, request=request)
            try:
                return HttpResponse(json.dumps(fh.rebuildData()))
            except Exception as err:
                return HttpResponse(json.dumps({'message': str(err)}), status=400)
    return HttpResponse(status=400)


@user_passes_test(test_func)
def get_links(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            try:
                link_model = cf_cache.only_fkey_models[request.GET['link_model']]
            except KeyError:
                try:
                    link_model = cf_cache.link_fields[request.GET['link_model']]['model']
                except KeyError:
                    return HttpResponse(status=400)
            link_objects = link_model.objects.all().order_by('-id')
            retval = [{'id': obj.id, 'name': str(obj)} for obj in link_objects]
            return HttpResponse(json.dumps(retval))
    return HttpResponse(status=400)


@user_passes_test(test_func)
def get_modules(request):
    teach_handlers = ['TeacherCustomFormModule', 'TeacherQuizModule']
    learn_handlers = ['StudentCustomFormModule']
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            try:
                prog = Program.objects.get(id=request.GET.get('program'))
            except Program.DoesNotExist:
                return HttpResponse(status=400)
            retval = {
                'learn': [
                    (mod.module.handler, mod.module.admin_title)
                    for mod in prog.getModules(tl='learn')
                    if mod.module.handler in learn_handlers
                ],
                'teach': [
                    (mod.module.handler, mod.module.admin_title)
                    for mod in prog.getModules(tl='teach')
                    if mod.module.handler in teach_handlers
                ],
            }
            return HttpResponse(json.dumps(retval))
    return HttpResponse(status=400)