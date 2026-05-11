from django.http import HttpResponseRedirect
from django.urls import reverse
from esp.utils.web import render_to_response
from esp.qsd.models import QuasiStaticData
from esp.qsd.forms import QSDMoveForm, QSDBulkMoveForm
from esp.users.models import admin_required
from reversion import revisions as reversion

@reversion.create_revision()
@admin_required
def manage_pages(request):
    if request.method == 'POST':
        data = request.POST
        if request.GET['cmd'] == 'bulk_move':
            if 'confirm' in data:
                form = QSDBulkMoveForm(data)
                #   Handle submission of bulk move form
                if form.is_valid():
                    form.save_data()
                    return HttpResponseRedirect(reverse('manage_pages'))

            #   Create and display the form
            qsd_id_list = []
            for key in data.keys():
                if key.startswith('check_'):
                    qsd_id_list.append(int(key[6:]))
            if len(qsd_id_list) > 0:
                form = QSDBulkMoveForm()
                qsd_list = QuasiStaticData.objects.filter(id__in=qsd_id_list)
                common_path = form.load_data(qsd_list)
                if common_path:
                    return render_to_response('qsd/bulk_move.html', request, {'common_path': common_path, 'qsd_list': qsd_list, 'form': form})

        qsd = QuasiStaticData.objects.get(id=request.GET['id'])
        if request.GET['cmd'] == 'move':
            #   Handle submission of move form
            form = QSDMoveForm(data)
            if form.is_valid():
                form.save_data()
            else:
                return render_to_response('qsd/move.html', request, {'qsd': qsd, 'form': form})
        elif request.GET['cmd'] == 'delete':
            #   Mark as inactive all QSD pages matching the one with ID request.GET['id']
            if data['sure'] == 'True':
                all_qsds = QuasiStaticData.objects.filter(url=qsd.url, name=qsd.name)
                for q in all_qsds:
                    q.disabled = True
                    q.save()
        return HttpResponseRedirect(reverse('manage_pages'))

    elif 'cmd' in request.GET:
        qsd = QuasiStaticData.objects.get(id=request.GET['id'])
        if request.GET['cmd'] == 'delete':
            #   Show confirmation of deletion
            return render_to_response('qsd/delete_confirm.html', request, {'qsd': qsd})
        elif request.GET['cmd'] == 'undelete':
            #   Make all the QSDs enabled and return to viewing the list
            all_qsds = QuasiStaticData.objects.filter(url=qsd.url, name=qsd.name)
            for q in all_qsds:
                q.disabled = False
                q.save()
        elif request.GET['cmd'] == 'move':
            #   Show move form
            form = QSDMoveForm()
            form.load_data(qsd)
            return render_to_response('qsd/move.html', request, {'qsd': qsd, 'form': form})

    #   Show QSD listing
    qsd_ids = []
    qsds = QuasiStaticData.objects.all().order_by('-create_date').values_list('id', 'url', 'name')
    seen_keys = set()
    for id, path, name in qsds:
        key = path, name
        if key not in seen_keys:
            qsd_ids.append(id)
            seen_keys.add(key)
    qsd_list = list(QuasiStaticData.objects.filter(id__in=qsd_ids))
    qsd_list.sort(key=lambda q: q.url)
    return render_to_response('qsd/list.html', request, {'qsd_list': qsd_list})
