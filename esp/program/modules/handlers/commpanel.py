from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django import forms
from django.core.cache import cache
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser
from django.db.models.query import Q, QNot
from django.template.defaultfilters import urlencode
from django.template import Context, Template
from esp.miniblog.models import Entry

class DBList(object):
    totalnum = False
    def count(self, override = False):
        from esp.users.models import User
        cache_id = urlencode('DBListCount: %s' % (self.key))
        
        if self.QObject:
            if not self.totalnum:
                if override:
                    self.totalnum = User.objects.filter(self.QObject).distinct().count()
                    cache.set(cache_id, self.totalnum, 60)
                else:
                    cachedval = cache.get(cache_id)
                    if cachedval is None:
                        self.totalnum = User.objects.filter(self.QObject).distinct().count()
                        cache.set(cache_id, self.totalnum, 60)
                    else:
                        self.totalnum = cachedval

            return self.totalnum
        else:
            return 0
        
    def id(self):
        return self.key
    
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __cmp__(self, other):
        return cmp(self.count(), other.count())
    
    def __str__(self):
        return self.key
        return "<DBList: %s: \"%s\" (%s total)>\n" % (self.key, self.description, self.count())

class CommModule(ProgramModuleObj):


    def students(self,QObject = False):
        if QObject:
            return {'satprepinfo': Q(satprepreginfo__program = self.program)}
        students = ESPUser.objects.filter(satprepreginfo__program = self.program).distinct()
        return {'satprepinfo': students }

    def isCompleted(self):
        
	satPrep = SATPrepRegInfo.getLastForProgram(self.user, self.program)
	return satPrep.id is not None

    @needs_admin
    def commfinal(self, request, tl, one, two, module, extra, prog):
        from django.template import Context, Template
        
        announcements = self.program.anchor.tree_create(['Announcements'])
        ids, subject, body  = [request.POST['userids'],
                               request.POST['subject'],
                               request.POST['body']    ]


        if request.POST.has_key('from') and \
           len(request.POST['from'].strip()) > 0:
            fromemail = request.POST['from']
        else:
            fromemail = None

        users = list(ESPUser.objects.filter(id__in = ids.split(',')).distinct())
        users.append(self.user)

        bodyTemplate    = Template(body)
        subjectTemplate = Template(subject)

        for user in users:
            
            anchor = announcements.tree_create([user.id])
            context_dict = {'name': ESPUser(user).name() }
            context = Context(context_dict)
            
            newentry = Entry(content   = bodyTemplate.render(context),
                             title     = subjectTemplate.render(context),
                             anchor    = anchor,
                             email     = True,
                             sent      = False,
                             fromuser  = self.user,
                             fromemail = fromemail
                            )

            newentry.save()

            newentry.subscribe_user(user)
        from django.conf import settings
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            est_time = settings.EMAILTIMEOUT * len(users)
        else:
            est_time = 1.5 * len(users)
            

        #        assert False, self.baseDir()+'finished.html'
        return render_to_response(self.baseDir()+'finished.html', request,
                                  (prog, tl), {'time': est_time})



    @needs_admin
    def commstep2(self, request, tl, one, two, module, extra, prog):
        import operator

        lists = self.program.getLists(True)
        
        opmapping = {'and'  : operator.and_,
                     'or'   : operator.or_,
                     'not'  : QNot,
                     'ident': (lambda x: x)
                     }
        keys = request.POST['keys'].split(',,')

        curList = lists[request.POST['base_list']]['list']
        stringrep = '%s' % (lists[request.POST['base_list']]['list'])

        separated = {'or': [curList], 'and': []}
        
        for key in keys:
            if request.POST.has_key('operator_'+key) and \
               request.POST['operator_'+key] and \
               request.POST['operator_'+key] != 'ignore':
                separated[request.POST['operator_'+key]].append(opmapping[request.POST['not_'+key]](lists[key]['list']))


        for i in range(len(separated['or'])):
            for j in range(len(separated['and'])):
                separated['or'][i] = opmapping['and'](separated['or'][i], separated['and'][j])
                
        curList = separated['or'][0]
        for List in separated['or'][1:]:
            curList = opmapping['or'](curList, List)
        
    
        
                                                               
        return render_to_response(self.baseDir()+ 'step2.html', request, (prog, tl),
                                  {'ids': [x['id'] for x in ESPUser.objects.filter(curList).values('id')]})
        

    @needs_admin
    def maincomm(self, request, tl, one, two, module, extra, prog):

        arrLists = []
        lists = self.program.getLists(True)
        for key, value in lists.items():
            arrLists.append(DBList(key = key, QObject = value['list'], description = value['description'].strip('.')))
            
        arrLists.sort(reverse=True)
        
        return render_to_response(self.baseDir()+'commmodulefront.html', request, (prog, tl), {'lists': arrLists})

    @needs_student
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
	manipulator = SATPrepInfoManipulator()
	new_data = {}
	if request.method == 'POST':
		new_data = request.POST.copy()
		
		errors = manipulator.get_validation_errors(new_data)
		
		if not errors:
			manipulator.do_html2python(new_data)
			new_reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
			new_reginfo.addOrUpdate(new_data, request.user, prog)

                        return self.goToCore(tl)
	else:
		satPrep = SATPrepRegInfo.getLastForProgram(request.user, prog)
		
		new_data = satPrep.updateForm(new_data)
		errors = {}

	form = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response('program/modules/satprep_stureg.html', request, (prog, tl), {'form':form})

