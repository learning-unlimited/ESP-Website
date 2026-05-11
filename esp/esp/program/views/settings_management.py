from esp.utils.web import render_to_response
from esp.program.forms import TagSettingsForm, RedirectForm, PlainRedirectForm, CategoryForm, FlagTypeForm, RecordTypeForm
from esp.users.models import admin_required, RecordType
from django.contrib.sites.models import Site
from django.contrib.redirects.models import Redirect
from esp.dbmail.models import PlainRedirect
from esp.program.models import ClassCategories, ClassFlagType

@admin_required
def tags(request, section=""):
    context = {}

    #If one of the forms was submitted, process it and save if valid
    if request.method == 'POST':
        form = TagSettingsForm(request.POST)
        if form.is_valid():
            form.save()
            form = TagSettingsForm() # replace null responses with defaults if processed successfully
    else:
        form = TagSettingsForm()

    context['form'] = form
    context['categories'] = form.categories
    context['open_section'] = section

    return render_to_response('program/modules/admincore/tags.html', request, context)

@admin_required
def redirects(request, section=""):
    """
    View that lets admins create/edit URL and email redirects
    """
    context = {}
    redirect_form = RedirectForm()
    email_redirect_form = PlainRedirectForm()

    if request.method == 'POST':
        if request.POST.get('object') == 'redirect':
            section = 'redirects'
            if request.POST.get('command') == 'add': # New redirect
                redirect_form = RedirectForm(request.POST)
                if redirect_form.is_valid():
                    redirect = redirect_form.save(commit=False)
                    redirect.site = Site.objects.get_current()
                    redirect.save()
                    redirect_form = RedirectForm()
            elif request.POST.get('command') == 'load': # Load existing redirect into form
                redirect_id = request.POST.get('id')
                redirects = Redirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect_form = RedirectForm(instance = redirect)
            elif request.POST.get('command') == 'edit': # Edit existing redirect
                redirect_id = request.POST.get('id')
                redirects = Redirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect_form = RedirectForm(request.POST, instance = redirect)
                    if redirect_form.is_valid():
                        redirect_form.save()
                        redirect_form = RedirectForm()
            elif request.POST.get('command') == 'delete': # Delete redirect
                redirect_id = request.POST.get('id')
                redirects = Redirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect.delete()
        elif request.POST.get('object') == 'email_redirect':
            section = 'email_redirects'
            if request.POST.get('command') == 'add': # New email redirect
                email_redirect_form = PlainRedirectForm(request.POST)
                if email_redirect_form.is_valid():
                    email_redirect_form.save()
                    email_redirect_form = PlainRedirectForm()
            elif request.POST.get('command') == 'load': # Load existing email redirect into form
                redirect_id = request.POST.get('id')
                redirects = PlainRedirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    email_redirect_form = PlainRedirectForm(instance = redirect)
            elif request.POST.get('command') == 'edit': # Edit existing email redirect
                redirect_id = request.POST.get('id')
                redirects = PlainRedirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    email_redirect_form = PlainRedirectForm(request.POST, instance = redirect)
                    if email_redirect_form.is_valid():
                        email_redirect_form.save()
                        email_redirect_form = PlainRedirectForm()
            elif request.POST.get('command') == 'delete': # Delete email redirect
                redirect_id = request.POST.get('id')
                redirects = PlainRedirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect.delete()
    context['open_section'] = section
    context['redirect_form'] = redirect_form
    context['email_redirect_form'] = email_redirect_form
    context['redirects'] = Redirect.objects.all()
    context['email_redirects'] = PlainRedirect.objects.all()

    return render_to_response('program/redirects.html', request, context)

@admin_required
def catsflagsrecs(request, section=""):
    """
    View that lets admins create/edit class categories and flag types
    """
    context = {}
    cat_form = CategoryForm(initial={'symbol': ''})
    flag_form = FlagTypeForm()
    rec_form = RecordTypeForm()

    if request.method == 'POST':
        if request.POST.get('object') == 'category':
            section = 'categories'
            if request.POST.get('command') == 'add': # New category
                cat_form = CategoryForm(request.POST)
                if cat_form.is_valid():
                    cat_form.save()
                    cat_form = CategoryForm()
            elif request.POST.get('command') == 'load': # Load existing category into form
                cat_id = request.POST.get('id')
                cats = ClassCategories.objects.filter(id = cat_id)
                if cats.count() == 1:
                    cat = cats[0]
                    cat_form = CategoryForm(instance = cat)
            elif request.POST.get('command') == 'edit': # Edit existing category
                cat_id = request.POST.get('id')
                cats = ClassCategories.objects.filter(id = cat_id)
                if cats.count() == 1:
                    cat = cats[0]
                    cat_form = CategoryForm(request.POST, instance = cat)
                    if cat_form.is_valid():
                        cat_form.save()
                        cat_form = CategoryForm()
            elif request.POST.get('command') == 'delete': # Delete category
                cat_id = request.POST.get('id')
                cats = ClassCategories.objects.filter(id = cat_id)
                if cats.count() == 1:
                    cat = cats[0]
                    cat.delete()
        elif request.POST.get('object') == 'flag_type':
            section = 'flagtypes'
            if request.POST.get('command') == 'add': # New flag type
                flag_form = FlagTypeForm(request.POST)
                if flag_form.is_valid():
                    flag_form.save()
                    flag_form = FlagTypeForm()
            elif request.POST.get('command') == 'load': # Load existing flag type into form
                ft_id = request.POST.get('id')
                fts = ClassFlagType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    flag_form = FlagTypeForm(instance = ft)
            elif request.POST.get('command') == 'edit': # Edit existing flag type
                ft_id = request.POST.get('id')
                fts = ClassFlagType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    flag_form = FlagTypeForm(request.POST, instance = ft)
                    if flag_form.is_valid():
                        flag_form.save()
                        flag_form = FlagTypeForm()
            elif request.POST.get('command') == 'delete': # Delete flag type
                ft_id = request.POST.get('id')
                fts = ClassFlagType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    ft.delete()
        elif request.POST.get('object') == 'record_type':
            section = 'recordtypes'
            if request.POST.get('command') == 'add': # New record type
                rec_form = RecordTypeForm(request.POST)
                if rec_form.is_valid():
                    rec_form.save()
                    rec_form = RecordTypeForm()
            elif request.POST.get('command') == 'load': # Load existing record type into form
                ft_id = request.POST.get('id')
                fts = RecordType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    rec_form = RecordTypeForm(instance = ft)
            elif request.POST.get('command') == 'edit': # Edit existing record type
                rt_id = request.POST.get('id')
                rts = RecordType.objects.filter(id = rt_id)
                if rts.count() == 1:
                    rt = rts[0]
                    rec_form = RecordTypeForm(request.POST, instance = rt)
                    if rec_form.is_valid():
                        rec_form.save()
                        rec_form = RecordTypeForm()
            elif request.POST.get('command') == 'delete': # Delete record type
                rt_id = request.POST.get('id')
                rts = RecordType.objects.filter(id = rt_id)
                if rts.count() == 1:
                    rt = rts[0]
                    rt.delete()
    context['open_section'] = section
    context['cat_form'] = cat_form
    context['flag_form'] = flag_form
    context['rec_form'] = rec_form
    context['categories'] = ClassCategories.objects.all().order_by('seq')
    context['flag_types'] = ClassFlagType.objects.all().order_by('seq')
    rec_types = RecordType.objects.all().order_by('id')
    context['record_types'] = sorted(rec_types, key = lambda x:x.is_custom(), reverse=True)

    return render_to_response('program/categories_and_flags.html', request, context)
