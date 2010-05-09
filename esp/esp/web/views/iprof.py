from django.conf import settings
from esp.utils.profiler import Profiler
from django.http import HttpResponse, Http404
from esp.web.util import render_to_response
from itertools import groupby 

p = None
magic = 'voila'

def iprof(request):
    global p
    global magic

    if not getattr(settings, 'IPROF_ENABLED', False):
        raise Http404
        return

    if not (magic in request.REQUEST):
        raise Http404
        return

    sortnum = 1
    if 'sort' in request.REQUEST:
        try:
            sortnum = int(request.REQUEST['sort'])
        except ValueError:
            pass
    if sortnum < 1 or sortnum > 5:
      sortnum = 1


    msg = ''
    if 'install' in request.REQUEST:
        if p is None:
            p = Profiler()
            p.install()
            msg = 'Install successful. %d functions now being monitored.' % len(p.data)
        else:
            msg = 'Profiler already installed (%d functions monitored)' % len(p.data)
    elif 'uninstall' in request.REQUEST:
        if p is None:
            msg = 'Nothing to uninstall'
        else:
            counts = p.uninstall()
            p = None
            msg = 'Uninstall removed %d of %d hooks.' % counts
            if counts[0] != counts[1]:
                msg += " (INCOMPLETE)"
    elif 'clear' in request.REQUEST:
        if p:
            p.clear()
            msg = 'Cleared successfully'
        else:
            msg = 'Nothing to clear'

    context = {}
    context['msg'] = msg
    context['magic'] = magic
    context['sortnum'] = sortnum
    iprof_results(sortnum, request, context)

    if len(msg) > 0:
        response = HttpResponse(msg, mimetype='text/html')
    elif 'ajax' in request.REQUEST:
        response = HttpResponse(context['nicedata_table'], mimetype='text/html')
    else:
        response = render_to_response('iprof.html', request, None, context)

    response['Pragma'] = 'no-cache'
    response['Cache-Control'] = 'no-cache'
    response['Expires'] = '-1'
    return response



def iprof_results(sortnum, request, context):
    global p
    global magic

    # Take a snapshot of the data
    nicedata = []
    if p:
        overhead = delta2sec(p.overhead_dt)/p.overhead_ncalls
        count = 0
        for func, path, ncalls, icalls, total, inner in p.data.itervalues():
            if count > 40 and ncalls <= 0:
                continue
            den = ncalls if ncalls > 0 else 1
            total = delta2sec(total) - overhead*ncalls
            inner = delta2sec(inner)
            nicedata.append([path[0], path[1],
                             ncalls, icalls, 
                             total, total-inner,
                             total/den, (total-inner)/den ])
            count += 1

    if 'group_by_module' in request.REQUEST:
        nicedata.sort(None, lambda x: x[0])
        mdata = []
        for mod,rows in groupby(nicedata, key=lambda x: x[0]):
            mcur = [ mod, '---', 0, 0, 0, 0, None, None ]
            for r in rows:
                mcur[2] += r[2]
                mcur[3] += r[3]
                mcur[4] += r[4]
                mcur[5] += r[5]
            # Calculate "per call" values
            den = mcur[2] if mcur[2] > 0 else 1
            mcur[6] = mcur[4] / den
            mcur[7] = mcur[5] / den
            mdata.append(mcur)
        nicedata = mdata

    def sortfunc(x):
        return x[1+sortnum]

    nicedata.sort(None, sortfunc, True)

    tbl = '';
    tbl += '<tr>'
    tbl += '<th>Module</th>'
    tbl += '<th>Function</th>'
    tbl += '<th><a id="sort1" href="javascript:sort1()"># of Calls</a></th>'
    tbl += '<th><a id="sort2" href="javascript:sort2()">Inner Calls</a></th>'
    tbl += '<th><a id="sort3" href="javascript:sort3()">Total Time</a></th>'
    tbl += '<th><a id="sort4" href="javascript:sort4()">Proper Time</a></th>'
    tbl += '<th><a id="sort5" href="javascript:sort5()">Total Time / Call</a></th>'
    tbl += '<th><a id="sort6" href="javascript:sort6()">Proper Time / Call</a></th>'
    tbl += '</tr>'
    tbl += "\n"
    for row in nicedata:
        tbl += '<tr>';
        tbl += '<td>' + str(row[0]) + '</td>'
        tbl += '<td>' + str(row[1]) + '</td>'
        tbl += '<td>%d</td>' % row[2]
        tbl += '<td>%d</td>' % row[3]
        tbl += '<td>%.6f</td>' % row[4]
        tbl += '<td>%.6f</td>' % row[5]
        tbl += '<td>%.6f</td>' % row[6]
        tbl += '<td>%.6f</td>' % row[7]
        tbl += '</tr>'
        tbl += "\n"

    context['nicedata_table'] = tbl

    return


def delta2sec(d):
  return d.days*24*3600 + d.seconds + d.microseconds/1000000.0;

