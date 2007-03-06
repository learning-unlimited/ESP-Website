from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode
from esp.users.models    import ESPUser, User
from esp.users.views import search_for_user, get_user_list
from django.http import HttpResponseRedirect
from django import forms
from esp.program.models import SATPrepRegInfo, Class, ClassCategories



class SATPrepAdminSchedule(ProgramModuleObj):
    """ This allows SATPrep directors to schedule their programs using
        an algorithm. """
    def extensions(self):
        return [('satprepInfo', module_ext.SATPrepAdminModuleInfo)]

    @needs_admin
    def schedule_options(self, request, tl, one, two, module, extra, prog):
        """ This is a list of the two options required to schedule an
            SATPrep class. """
        
        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {})

    @needs_admin
    def satprep_schedulestud(self, request, tl, one, two, module, extra, prog):
        """ An interface for scheduling all the students! """

        import string

        if not request.method == 'POST' and not request.POST.has_key('schedule_confirm'):
            return render_to_response(self.baseDir()+'schedule_confirm.html', request, (prog, tl), {})

        num_divisions = self.satprepInfo.num_divisions

        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        # got a list of users
        import random
        users = list(filterObj.getList(User).distinct())
        random.shuffle(users)

        user_scores = []

        for user in users:
            satprepreginfo = SATPrepRegInfo.getLastForProgram(user, self.program)
            user_scores.append({'user': user,
                                'math': SATPrepAdminSchedule.getScore(satprepreginfo, 'math'),
                                'writ': SATPrepAdminSchedule.getScore(satprepreginfo, 'writ'),
                                'verb': SATPrepAdminSchedule.getScore(satprepreginfo, 'verb')})

        def cmp_scores(test):
            def _cmp(one, two):
                return cmp(one[test], two[test])

            return _cmp

        separated_list = {'math': {'none': [x['user'] for x in user_scores if x['math'] is None]},
                          'verb': {'none': [x['user'] for x in user_scores if x['verb'] is None]},
                          'writ': {'none': [x['user'] for x in user_scores if x['writ'] is None]}}

        

        sections = list(string.ascii_uppercase[0:num_divisions])
        sections.sort(reverse = True)
        
        for test in ['math','verb','writ']:
            cur_list = [x for x in user_scores if x[test] is not None]
            cur_list.sort(cmp_scores(test))

            num_each = len(cur_list) / num_divisions

            for i in range(len(cur_list)):
                section_num = i / num_each
                if section_num == num_divisions:
                    section_num -= 1

                cur_section = sections[section_num]

                if separated_list[test].has_key(cur_section):
                    separated_list[test][cur_section].append((cur_list[i]['user'],cur_list[i][test]))
                else:
                    separated_list[test][cur_section] = [(cur_list[i]['user'],cur_list[i][test])]
                    

        class_list = {'verb': {}, 'writ': {}, 'math': {}}

        for cls in list(self.program.classes()):
            try:
                test, section = cls.class_info.split('-')
            except:
                pass

            if class_list[test[0:4].lower()].has_key(section):
                class_list[test[0:4].lower()][section].append({'cls': cls,'numstudents': 0})
            else:
                class_list[test[0:4].lower()][section] = [ {'cls': cls,'numstudents': 0} ] 



        schedule = {} # userids -> list of time ids

        test = 'writ'
        for test in ['writ','math','verb']:
        #if test == 'writ':
            new_list = separated_list[test]
            for section, userList in new_list.items():
                if section != 'none':
                    clsList = class_list[test][section]
                    for user, score in userList:
                        if not schedule.has_key(user.id):
                            schedule[user.id] = []

                        cls = SATPrepAdminSchedule.getSmallestClass(clsList, schedule[user.id])
                        cls['numstudents'] += 1
                        cls['cls'].preregister_student(user)
                        cls['cls'].update_cache_students()
                        for ts in cls['cls'].meeting_times.all():
                            schedule[user.id].append(ts.id)

        return HttpResponseRedirect('/manage/%s/schedule_options' % self.program.getUrlBase())

    
    @staticmethod
    def getSmallestClass(clsList, schedule):
        import random

        # filter out classes that don't meet the schedule
        if len(schedule) > 0:
            clsList = [cls for cls in clsList if
                       len(set(x['id'] for x in cls['cls'].meeting_times.all().values('id'))
                        & set(schedule)) == 0 ]
        
                       
        
        num_students = clsList[0]['numstudents']

        

        for i in range(1, len(clsList)):
            if num_students > clsList[i]['numstudents']:
                num_students = clsList[i]['numstudents']

        cls_winner = random.choice([ x for x in clsList
                                     if x['numstudents'] == num_students ])
        return cls_winner
                      
        
        
    @staticmethod
    def getScore(satprepreginfo, test):
        """ Get the score corresponding to 'test' for a specific user. """
        cur_score = satprepreginfo.__dict__['diag_%s_score' % test]

        if cur_score is not None and cur_score >= 200 and cur_score <= 800:
            return cur_score

        cur_score = satprepreginfo.__dict__['old_%s_score' % test]

        if cur_score is not None and cur_score >= 200 and cur_score <= 800:
            return cur_score

        return None
           
        
        
        
    @needs_admin
    def satprep_classgen(self, request, tl, one, two, module, extra, prog):
        """ This view will generate the classes for all the users. """

        if not request.method == 'POST' and not request.POST.has_key('newclass_create'):
            return render_to_response(self.baseDir()+'newclass_confirm.html', request, (prog, tl), {})

        # delete current classes
        cur_classes = Class.objects.filter(parent_program = self.program)
        [ cls.delete() for cls in cur_classes]

        # get the list of users we're generating for
        user_list =  self.program.getLists()['teachers_satprepinfo']['list']

        timeslots = self.program.getTimeSlots()

        dummy_anchor = self.program.anchor.tree_create(['DummyClass'])
        dummy_anchor.save()
        
        for user in user_list:
            
            satprepmodule = module_ext.SATPrepTeacherModuleInfo.objects.get(program = self.program, user = user)
            if satprepmodule.section is None or len(satprepmodule.section.strip()) == 0:
                pass

            for timeslot in timeslots:
                # now we create a new class for each timeslot

                newclass = Class()
                newclass.parent_program = self.program
                newclass.duration       = 0
                newclass.class_info     = '%s-%s' % (satprepmodule.get_subject_display(),
                                                     satprepmodule.section)
                newclass.grade_min      = 6
                newclass.grade_max      = 12

                newclass.class_size_min = 0
                newclass.class_size_max = 0
                
                newclass.category = ClassCategories.objects.get(category = 'SATPrep')
                newclass.anchor = dummy_anchor

                newclass.enrollment = 0
                newclass.save()
                                
                nodestring = 'SAT' + str(newclass.id)
                newclass.anchor = self.program.classes_node().tree_create([nodestring])
                newclass.anchor.friendly_name = 'SATPrep %s-%s' % (satprepmodule.get_subject_display(),
                                                                   satprepmodule.section)
                newclass.anchor.save()

                newclass.anchor.save()
                newclass.anchor.tree_create(['TeacherEmail'])
                newclass.save()

                #cache this result
                newclass.update_cache()

                # ensure multiselect fields are set
                newclass.viable_times.clear()
                newclass.resources.clear()


                # add the appropriate timeslots
                newclass.viable_times.add(timeslot)
                newclass.meeting_times.add(timeslot)

                    
                # add userbits
                newclass.makeTeacher(user)

                newclass.accept()

        dummy_anchor.delete()
        return HttpResponseRedirect('/manage/%s/schedule_options' % self.program.getUrlBase())
        
    def satprep_teachassign(self, request, tl, one, two, module, extra, prog):
        """ This will allow the program director to assign sections to teachers. """
        import string

        #SATPrepTeacherModuleInfo
        # get teachers
        user_list =  self.program.getLists()['teachers_satprepinfo']['list']
        #assert False
        if request.method == 'POST' and request.POST.has_key('teacher_section_form'):
            for user in user_list:
                if request.POST.has_key(('section__%s' % user.id)):

                    satprepmodule = module_ext.SATPrepTeacherModuleInfo.objects.get(program = self.program, user = user)
                    satprepmodule.section = request.POST['section__%s' % user.id]
                    satprepmodule.save()


            return HttpResponseRedirect('/manage/%s/schedule_options' % self.program.getUrlBase())

        retList = []

        for user in user_list:
            retList.append({'user':          ESPUser(user),
                            'satprepmodule': module_ext.SATPrepTeacherModuleInfo.objects.get(program = self.program, user = user)})

        def sorter(one, two):
            cmp1 = cmp(one['satprepmodule'].get_subject_display(),
                       two['satprepmodule'].get_subject_display())

            if cmp1 != 0:
                return cmp1

            cmp1 = cmp(one['satprepmodule'].section,
                       two['satprepmodule'].section)
            
            if cmp1 != 0:
                return cmp1

            cmp1 = cmp(one['user'], two['user'])

            return cmp1

        retList.sort(sorter)
                
            
        sections = list(string.ascii_uppercase[:self.satprepInfo.num_divisions])

        context = {'users': retList, 'sections': sections }

        return render_to_response(self.baseDir()+'setteachers.html', request, (prog, tl), context)
