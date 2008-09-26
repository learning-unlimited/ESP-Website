
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode
from esp.users.models    import ESPUser, User
from esp.users.views import search_for_user, get_user_list
from django.http import HttpResponseRedirect
from esp.program.models import SATPrepRegInfo, ClassSubject, ClassCategories
from esp.cal.models import Event
from esp.resources.models import Resource, ResourceType
from esp.datatree.models import DataTree


class SATPrepAdminSchedule(ProgramModuleObj, module_ext.SATPrepAdminModuleInfo):
    """ This allows SATPrep directors to schedule their programs using
        an algorithm. """
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Schedule SATPrep",
            "module_type": "manage",
            "seq": 1000
            }
    
    def extensions(self):
        return [('satprepInfo', module_ext.SATPrepAdminModuleInfo)]

    @main_call
    @needs_admin
    def schedule_options(self, request, tl, one, two, module, extra, prog):
        """ This is a list of the two options required to schedule an
            SATPrep class. """
        
        return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {})

    @aux_call
    @needs_admin
    def create_rooms(self, request, tl, one, two, module, extra, prog):
        """ Step 1 of the diagnostic setup process. """
        
        #   Show a page asking for a list of rooms and their capacities.
        
        if request.method == 'POST':
            #   Receive the data and create a series of rooms in the specified timeslot.
            data = request.POST.copy()
            timeslot_id = int(data.get('timeslot'))
            empty_rooms = data.get('empty_rooms')
            rooms = data.get('rooms')
            room_list = rooms.split('\n')
            
            timeslot = Event.objects.get(id=timeslot_id)
            classroom_rt = ResourceType.get_or_create('Classroom')
        
            for s in room_list:
                #   The rooms will be created without additional resources
                str_dir = s.split(',')
                if len(str_dir) == 2:
                    res = Resource()
                    res.name = str_dir[0]
                    res.res_type = classroom_rt
                    res.num_students = int(str_dir[1])
                    res.event = timeslot
                    res.save()
                        
            #   Redirect to the diagnostic sections page (step 2) excluding the last few rooms if desired.
            empty_rooms_list = []
            for t in room_list[(len(room_list) - int(empty_rooms)):]:
                str_dir = t.split(',')
                empty_rooms_list.append(str_dir[0])
            empty_rooms_str = ','.join(empty_rooms_list)

            return HttpResponseRedirect('/manage/%s/%s/diagnostic_sections?timeslot=%d&empty_rooms=%s' % (one, two, timeslot_id, empty_rooms_str))

        context = {'prog': prog, 'room_indices': range(0, 22)}
        return render_to_response(self.baseDir()+'room_setup.html', request, (prog, tl), context)
    
         

    @aux_call
    @needs_admin
    def diagnostic_sections(self, request, tl, one, two, module, extra, prog):
        """ Step 2 of the diagnostic setup process. """
        
        #   Initialize some stuff
        empty_rooms = request.GET['empty_rooms'].split(',')
        
        timeslot_id = int(request.GET['timeslot'])
        timeslot = Event.objects.get(id=timeslot_id)
        
        rooms = list(prog.getClassrooms(timeslot=timeslot).exclude(name__in=empty_rooms))
            
        #   Get student list, sort alphabetically
        students = list(prog.students()['confirmed'])
        num_students = len(students)
        students.sort(key=lambda s: s.last_name)
        
        debug_str = ''
        total_size = 0
        accum_capacity = {}
        
        #   Count cumulative capacity of rooms encountered so far
        for r in rooms:
            total_size += r.num_students
            accum_capacity[r.id] = total_size - r.num_students
            
        #   Reverse the list so you know how much space is remaining
        rooms.reverse()
        for r in rooms:
            r.add_students = num_students * r.num_students / total_size
            
        #   Iterate over the rooms, adding students until the number of students remaining
        #   matches the proportion of space remaining
        sections = []
        students_remaining = num_students
        i = 0
        j = 0
        for r in rooms:
            new_section = {'timeslot': timeslot, 'students': [], 'room': r, 'index': i}
            new_class = ClassSubject()
            new_class.parent_program = prog
            new_class.class_size_max = r.num_students
            new_class.duration = timeslot.duration().seconds / 3600.0
            new_class.grade_min = 9
            new_class.grade_max = 12
            new_class.anchor = DataTree.get_by_uri(prog.anchor.uri+'/Classes/Diag'+str(i+1), create=True)
            new_class.category = ClassCategories.objects.get(category='SATPrep')
            new_class.status = 10
            new_class.save()
            new_sec = new_class.add_default_section()
            
            new_sec.meeting_times.add(timeslot)
            new_sec.assignClassRoom(r)
            while students_remaining > (accum_capacity[r.id] * num_students / total_size):
                debug_str += 'i=%d %d/%d ac=%d\n' % (i, j, num_students, accum_capacity[r.id])
                new_sec.preregister_student(students[j])
                new_section['students'].append(students[j])
                j += 1
                students_remaining -= 1
            if len(new_section['students']) > 0:
                new_section['fln'] = new_section['students'][0].last_name
                new_section['lln'] = new_section['students'][-1].last_name
                new_class.anchor.friendly_name = 'SAT Prep Diagnostic %d: %s - %s' % (i + 1, new_section['fln'], new_section['lln'])
                new_class.anchor.save()
            i += 1
            sections.append(new_section)
       
        context = {'prog': prog, 'sections': sections}
        return render_to_response(self.baseDir()+'diagnostic_sections.html', request, (prog, tl), context)


    @aux_call
    @needs_admin
    def enter_scores(self, request, tl, one, two, module, extra, prog):
        """ Allow bulk entry of scores from a spreadsheet.  This works for either the diagnostic or
        practice exams. """
        
        from esp.program.modules.forms.satprep import ScoreUploadForm
        from esp.program.models import SATPrepRegInfo
        
        #   The scores should be saved in SATPrepRegInfos with the following fields:
        #   user, program, and lookup the rest here...
        reginfo_fields = {'diag_m': 'diag_math_score', 'diag_v': 'diag_verb_score', 'diag_w': 'diag_writ_score',
                          'prac_m': 'prac_math_score', 'prac_v': 'prac_verb_score', 'prac_w': 'prac_writ_score'}
        
        context = {}
        form = ScoreUploadForm()
        
        if request.method == 'POST':
            data = request.POST.copy()
            data.update(request.FILES)
            form = ScoreUploadForm(data)
            
            if form.is_valid():
                prefix = form.cleaned_data['test'] + '_'
                
                #   Check that at least one of the input methods is being used.
                #   Copy over the content from the text box, then the file.
                if len(form.cleaned_data['text']) > 3:
                    content = form.cleaned_data['text']
                elif form.cleaned_data['file'] and form.cleaned_data['file'].has_key('content'):
                    content = form.cleaned_data['file']['content']
                else:
                    from esp.middleware import ESPError
                    raise ESPError(False), 'You need to upload a file or enter score information in the box.  Please go back and do so.'
                
                lines = content.split('\n')
                error_lines = []
                error_reasons = []
                n = 0
                
                #   Read through the input string
                for line in lines:
                    error_flag = False
                    entry = line.split(',')
                    # Clean up a bit
                    entry = [s.strip() for s in entry]
                    entry = [s for s in entry if s != ""]
                    
                    #   Test the input data and report the error if there is one
                    if len(entry) < 3:
                        error_flag = True
                        error_lines.append(line)
                        error_reasons.append('Insufficient information in line.')
                        continue
                    
                    try:
                        id_num = int(entry[0])
                        student = User.objects.get(id=id_num)
                        entry.pop(0)
                    except ValueError:
                        student = prog.students()['confirmed'].filter(first_name__icontains=entry[1], last_name__icontains=entry[0])
                        if student.count() != 1:
                            error_flag = True
                            error_lines.append(line)
                            error_reasons.append('Found %d matching students in program.' % student.count())
                        else:
                            student = student[0]
                            entry = entry[2:] # pop entries
                    except User.DoesNotExist:
                        error_flag = True
                        error_lines.append(line)
                        error_reasons.append('Invalid user ID of %d.' % id_num)

                    if not error_flag:
                        reginfo = SATPrepRegInfo.getLastForProgram(student, prog)
                        got_some = False
                        while len(entry) > 1:
                            try:
                                category = entry[0].lower()[0]
                                score = int(entry[1])
                                field_name = reginfo_fields[prefix+category]
                                reginfo.__dict__[field_name] = score
                                got_some = True
                                entry = entry[2:] # pop entries
                            except KeyError, IndexError:
                                error_flag = True
                                error_lines.append(line)
                                error_reasons.append('Invalid category name: %s.' % entry[0])
                                break
                            except ValueError:
                                error_flag = True
                                error_lines.append(line)
                                error_reasons.append('Not an integer score: %s.' % entry[1])
                                break

                        if not error_flag:
                            if got_some:
                                #   Add the student's scores into the database
                                reginfo.save()
                                n += 1
                            else:
                                error_flag = True
                                error_lines.append(line)
                                error_reasons.append('Insufficient information in line.')
                        
                #   Summary information to display on completion
                context['errors'] = error_lines
                context['error_reasons'] = error_reasons
                context['complete'] = True
                context['num_updated'] = n

        #   Populate default information
        context['prog'] = prog
        context['module'] = self
        context['form'] = form
        
        return render_to_response(self.baseDir()+'score_entry.html', request, (prog, tl), context)


    @aux_call
    @needs_admin
    def satprep_schedulestud(self, request, tl, one, two, module, extra, prog):
        """ An interface for scheduling all the students, provided the classes have already
        been generated. """
        from esp.program.modules.module_ext import SATPrepTeacherModuleInfo
        import string
        import random
        
        def cmp_scores(test):
            def _cmp(one, two):
                return cmp(one[test], two[test])

            return _cmp

        #   Get confirmation and a list of users first.
        if not request.method == 'POST' and not request.POST.has_key('schedule_confirm'):
            return render_to_response(self.baseDir()+'schedule_confirm.html', request, (prog, tl), {})

        num_divisions = self.num_divisions

        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        #   Find the user's scores and put them in a python list.
        users = list(filterObj.getList(User).distinct())
        random.shuffle(users)
        user_scores = []
        for user in users:
            satprepreginfo = SATPrepRegInfo.getLastForProgram(user, self.program)
            user_scores.append({'user': user,
                                'math': SATPrepAdminSchedule.getScore(satprepreginfo, 'math'),
                                'writ': SATPrepAdminSchedule.getScore(satprepreginfo, 'writ'),
                                'verb': SATPrepAdminSchedule.getScore(satprepreginfo, 'verb')})

        separated_list = {'math': {'none': [x['user'] for x in user_scores if x['math'] is None]},
                          'verb': {'none': [x['user'] for x in user_scores if x['verb'] is None]},
                          'writ': {'none': [x['user'] for x in user_scores if x['writ'] is None]}}

        sections = list(string.ascii_uppercase[0:num_divisions])
        sections.sort(reverse = True)
        
        #   Divide the users into sections.
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

        #   Retrieve the class sections of the program, keeping track of their subject and level
        #   in the class_list dictionary.
        tmi = SATPrepTeacherModuleInfo.objects.filter(program=prog)

        class_list = {'verb': {}, 'writ': {}, 'math': {}}
        for t in tmi:
            section = t.section
            subject = t.get_subject_display().lower()[:4]
            cl = ESPUser(t.user).getTaughtClasses(prog)
            for c in cl:
                for s in c.sections.all():
                    if class_list[subject].has_key(section):
                        class_list[subject][section].append({'cls': s, 'numstudents': 0, 'maxstudents': s.room_capacity()})
                    else:
                        class_list[subject][section] = [{'cls': s, 'numstudents': 0, 'maxstudents': s.room_capacity()}] 
        
        schedule = {} # userids -> list of time ids

        dry_run = False
        scheduling_log = []
        sched_nums = {}

        #   Assign students one by one to the appropriate class section in each subject.
        for test in ['writ','math','verb']:
            sched_nums[test] = 0
            new_list = separated_list[test]
            for section, userList in new_list.items():
                if section != 'none':
                    clsList = class_list[test][section]
                    for user, score in userList:
                        if not schedule.has_key(user.id):
                            schedule[user.id] = []

                        cls = SATPrepAdminSchedule.getSmallestClass(clsList, schedule[user.id])
                        cls['numstudents'] += 1
                        sched_nums[test] += 1
                        scheduling_log.append('Added %s to %s at %s' % (user, cls['cls'], cls['cls'].meeting_times.all()[0]))

                        if not dry_run:
                            cls['cls'].preregister_student(user)
                            cls['cls'].update_cache_students()
                            
                        for ts in cls['cls'].meeting_times.all():
                            schedule[user.id].append(ts.id)

        return HttpResponseRedirect('/manage/%s/schedule_options' % self.program.getUrlBase())

    
    @staticmethod
    def getSmallestClass(clsList, schedule):
        import random

        #   Filter out classes that don't meet the schedule
        if len(schedule) > 0:
            clsList = [cls for cls in clsList if
                       len(set(x['id'] for x in cls['cls'].meeting_times.all().values('id'))
                        & set(schedule)) == 0 ]
        
        #   Get the class with the lowest percentage fullness.
        frac_students = clsList[0]['numstudents'] / clsList[0]['maxstudents']

        for i in range(1, len(clsList)):
            if frac_students > (clsList[i]['numstudents'] / clsList[i]['maxstudents']):
                frac_students = clsList[i]['numstudents'] / clsList[i]['maxstudents']

        cls_winner = random.choice([ x for x in clsList
                                     if (x['numstudents'] / x['maxstudents']) == frac_students ])
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
           

    @aux_call
    @needs_admin
    def satprep_classgen(self, request, tl, one, two, module, extra, prog):
        """ This view will generate the classes for all the users. """

        delete = False

        if not request.method == 'POST' and not request.POST.has_key('newclass_create'):
            #   Show the form asking for a room number and capacity for each teacher.
            
            user_list =  self.program.getLists()['teachers_satprepinfo']['list']
            reginfos = [module_ext.SATPrepTeacherModuleInfo.objects.get(program=prog, user=u) for u in user_list]
            reginfos.sort(key=lambda x: x.subject + x.section)
            user_list = [r.user for r in reginfos]
            
            context = {'timeslots': prog.getTimeSlots(), 'teacher_data': zip([ESPUser(u) for u in user_list], reginfos)}
            
            return render_to_response(self.baseDir()+'newclass_confirm.html', request, (prog, tl), context)

        #   Delete current classes if specified (currently turned off, not necessary)
        if delete:
            cur_classes = ClassSubject.objects.filter(parent_program = self.program)
            [cls.delete() for cls in cur_classes]

        dummy_anchor = self.program_anchor_cached().tree_create(['DummyClass'])
        dummy_anchor.save()
        
        data = request.POST.copy()
        
        #   Pull the timeslots from the multiselect field on the form.
        timeslots = []
        for ts_id in data.getlist('timeslot_ids'):
            ts = Event.objects.get(id=ts_id)
            timeslots.append(ts)
        
        #   Create classrooms based on the form input.
        for key in data:
            key_dir = key.split('_')
            if len(key_dir) == 2 and key_dir[0] == 'room' and len(data[key]) > 0:
                #   Extract a room number and capacity from POST data.
                room_num = data.get(key)
                cap_key = 'capacity_' + key_dir[1]
                room_capacity = int(data.get(cap_key))
                reginfo = module_ext.SATPrepTeacherModuleInfo.objects.get(id=int(key_dir[1]))
                user = reginfo.user

                #   Initialize a class subject.
                newclass = ClassSubject()
                newclass.parent_program = self.program
                newclass.class_info     = '%s: Section %s (%s)' % (reginfo.get_subject_display(), reginfo.section,
                                                                   reginfo.get_section_display())
                newclass.grade_min      = 9
                newclass.grade_max      = 12
    
                newclass.class_size_min = 0
                newclass.class_size_max = room_capacity
                
                newclass.category = ClassCategories.objects.get(category = 'SATPrep')
                newclass.anchor = dummy_anchor
    
                newclass.save()
                                
                nodestring = 'SAT' + str(newclass.id)
                newclass.anchor = self.program.classes_node().tree_create([nodestring])
                newclass.anchor.friendly_name = 'SAT Prep %s - %s' % (reginfo.get_subject_display(),
                                                                   reginfo.get_section_display())
                newclass.anchor.save()
                newclass.anchor.tree_create(['TeacherEmail'])
                newclass.save()
                
                newclass.makeTeacher(user)
                newclass.accept()
    
                newclass.update_cache()
                    
                #   Create a section of the class for each timeslot.
                #   The sections are all held in the same room by default.  This can be changed
                #   in the scheduling module later.
                for ts in timeslots:
                    new_room = Resource()
                    new_room.name = room_num
                    new_room.res_type = ResourceType.get_or_create('Classroom')
                    new_room.num_students = room_capacity
                    new_room.event = ts
                    new_room.save()
                    sec = newclass.add_section(duration=(ts.duration().seconds / 3600.0))
                    sec.meeting_times.add(ts)
                    sec.assign_room(new_room)
        
        dummy_anchor.delete()
        return HttpResponseRedirect('/manage/%s/schedule_options' % self.program.getUrlBase())

    @aux_call
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
                
        sections = list(string.ascii_uppercase[:self.num_divisions])

        context = {'users': retList, 'sections': sections }

        return render_to_response(self.baseDir()+'setteachers.html', request, (prog, tl), context)

