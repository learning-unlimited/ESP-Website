
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.datatree.models import *
from esp.users.models    import ESPUser, User, UserBit
from esp.users.views import get_user_list
from django.http import HttpResponseRedirect
from esp.program.models import SATPrepRegInfo, ClassSubject, ClassCategories
from esp.cal.models import Event
from esp.resources.models import Resource, ResourceType
from esp.datatree.models import *


class SATPrepAdminSchedule(ProgramModuleObj, module_ext.SATPrepAdminModuleInfo):
    """ This allows SATPrep directors to schedule their programs using
        an algorithm. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "SATPrep Schedule Module",
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
            data = request.POST
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
            new_class.anchor = DataTree.get_by_uri(prog.anchor.get_uri()+'/Classes/Diag'+str(i+1), create=True)
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
    @login_required
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
                        del entry[0]
                    except ValueError:
                        student = prog.students()['confirmed'].filter(first_name__icontains=entry[1], last_name__icontains=entry[0])
                        if student.count() != 1:
                            error_flag = True
                            error_lines.append(line)
                            error_reasons.append('Found %d matching students in program.' % student.count())
                        else:
                            student = student[0]
			    del entry[0:2]
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
        import copy

        #   Get confirmation and a list of users first.
        if not request.method == 'POST' and not request.POST.has_key('schedule_confirm'):
            return render_to_response(self.baseDir()+'schedule_confirm.html', request, (prog, tl), {})

        filterObj, found = get_user_list(request, self.program.getLists(True))
        if not found:
            return filterObj

        #   Find the user's scores and put them in a python list.
        users = list(filterObj.getList(User).distinct())
        subjects = ['math', 'verb', 'writ']
        
        #   Expire existing enrollments
        reg_bits = UserBit.valid_objects().filter(verb=DataTree.get_by_uri('V/Flags/Registration/Enrolled')).filter(QTree(qsc__below=prog.anchor))
        """
        print 'Expiring %d enrollment bits' % reg_bits.count()
        """
        for bit in reg_bits:
            bit.expire()
        
        #   Add scores to each user
        for user in users:
            satprepreginfo = SATPrepRegInfo.getLastForProgram(user, self.program)
            user.scores = {}
            for subject in subjects:
                user.scores[subject] = SATPrepAdminSchedule.getScore(satprepreginfo, subject)

        #   Get an independently sorted list for each subject
        sorted_lists = {}
        for subject in subjects:
            sorted_lists[subject] = copy.deepcopy(users)
            sorted_lists[subject].sort(key=lambda x: x.scores[subject])
            
        #   Generate list of possible orderings
        def combinations(lst):
            if len(lst) == 1:
                return [lst]
            else:
                result = []
                for i in range(len(lst)):
                    other_items = [y for y in lst if y != lst[i]]
                    result += [[lst[i]] + x for x in combinations(other_items)]
                return result
        orderings = combinations(subjects)
            
        #   Divide students into orderings
        num_orderings = len(orderings)
        num_subjects = len(subjects)
        ordering_index = 0
        subject_index = 0
        def lists_non_empty():
            for subject in subjects:
                if len(sorted_lists[subject]) > 0:
                    return True
            return False
        ordering_lists = [[] for ordering in orderings]
        while lists_non_empty():
            #   Pull a student from the top of the list in the current subject
            new_student = sorted_lists[subjects[subject_index]].pop()
            #   Put them in the list for the current ordering
            ordering_lists[ordering_index].append(new_student)
            #   Remove them from the other lists
            for subject in subjects:
                if subject != subjects[subject_index]:
                    sorted_lists[subject].remove(new_student)
                    
            #   Debug statement:
            #   print 'Took %s (scores: %s) from %s list to ordering %s' % (new_student, new_student.scores, subjects[subject_index], orderings[ordering_index])
                    
            #   Move to the next subject list
            subject_index = (subject_index + 1) % num_subjects 
            #   Move to the next ordering list
            ordering_index = (ordering_index + 1) % num_orderings

        """
        #   Debug statements
        print '--------------'
        for i in range(num_orderings):
            print 'Ordering %s: %d students' % (orderings[i], len(ordering_lists[i]))
        """
        
        #   Retrieve the class sections of the program, keeping track of their subject and level
        #   in the class_list dictionary.
        tmi = SATPrepTeacherModuleInfo.objects.filter(program=prog)
        class_list = {}
        timeslots = prog.getTimeSlots()
        for timeslot in timeslots:
            class_list[timeslot] = {}
            for subject in subjects:
                class_list[timeslot][subject] = {}
        for t in tmi:
            section = t.section
            subject = t.get_subject_display().lower()[:4]
            cl = ESPUser(t.user).getTaughtClasses(prog)
            for c in cl:
                for s in c.get_sections():
                    timeslot = s.start_time()
                    if section not in class_list[timeslot][subject]:
                        class_list[timeslot][subject][section] = []
                    class_list[timeslot][subject][section].append((s, s.room_capacity()))

        """
        #   Debug statements
        #   print class_list
        """

        #   For each timeslot/subject combination, find the orderings that include it
        for timeslot_index in range(len(timeslots)):
            for subject in subjects:
                valid_orderings = filter(lambda o: o[timeslot_index] == subject, orderings)
                
                #   Get a list of students in those orderings sorted by their score in the current subject
                #   (Exclude students that have no score)
                timeslot = timeslots[timeslot_index]
                students = []
                for ordering in valid_orderings:
                    students += ordering_lists[orderings.index(ordering)]
                students = filter(lambda s: s.scores[subject] >= 200, students)
                students.sort(key=lambda s: s.scores[subject])
                students.reverse()
                
                """
                #   Debug statement
                print 'Timeslot %s; subject %s: %d students' % (timeslots[timeslot_index], subject, len(students))
                """
                
                #   Parcel out the spots in each level proportional to space
                num_students = len(students)
                num_spots = 0
                section_dict = class_list[timeslot][subject]
                level_space = {}
                level_thresholds = {}
                indiv_thresholds = {}
                ordered_sections = section_dict.keys()
                ordered_sections.sort()
                prev_section = None
                for section in ordered_sections:
                    level_space[section] = 0
                    for item in section_dict[section]:
                        num_spots += item[1]
                        level_space[section] += item[1]
                for section in ordered_sections:
                    if prev_section is None:
                        prev_threshold = 0
                    else:
                        prev_threshold = level_thresholds[prev_section]
                    section_size = level_space[section] * float(num_students) / num_spots
                    level_thresholds[section] = prev_threshold + section_size
                    indiv_thresholds[section] = [section_size * item[1] / level_space[section] + prev_threshold for item in section_dict[section]]
                    prev_section = section

                    """
                    #   Debug statement
                    #   print ' -> Section %s (%d/%d students): threshold = %f, indiv = %s' % (section, level_thresholds[section] - prev_threshold, level_space[section], level_thresholds[section], indiv_thresholds[section])
                    """

                #   Assign students
                num_students_assigned = 0
                section_index = 0
                current_item = 0
                for student in students:
                    if (section_index >= len(ordered_sections)):
                        raise ESPError(False), 'Overran number of sections'
                    current_section = ordered_sections[section_index]
                    if (current_item >= len(indiv_thresholds[current_section])):
                        raise ESPError(False), 'Overran number of sections in section'
                        
                    target_section = section_dict[current_section][current_item][0]
                    
                    if not hasattr(target_section, 'min_score'):
                        target_section.min_score = 800
                    if not hasattr(target_section, 'max_score'):
                        target_section.max_score = 200

                    target_section.preregister_student(student, overridefull=True)
                    if student.scores[subject] < target_section.min_score:
                        target_section.min_score = student.scores[subject]
                    if student.scores[subject] > target_section.max_score:
                        target_section.max_score = student.scores[subject]
                    
                    num_students_assigned += 1

                    """
                    #   Debug statements
                    print '  Assigning student %s (scores: %s) to %s' % (student, student.scores, target_section)
                    print '  -> %d assigned (current thresholds are %f, %f)' % (num_students_assigned, indiv_thresholds[current_section][current_item], level_thresholds[current_section])
                    """
                    
                    #   Increment section if necessary
                    if num_students_assigned > level_thresholds[current_section]:
                        section_index += 1
                        current_item = 0
                    #   Increment item if necessary
                    elif num_students_assigned > indiv_thresholds[current_section][current_item]:
                        current_item += 1

                """ 
                #   Check results
                for section in ordered_sections:
                    #   This code assumes multiple sections per level+timeblock+subject
                    print ' -> Section %s' % section
                    for item in section_dict[section]:
                        print '    (%d/%d) %s' % (item[0].num_students(), item[1], item[0])
                    
                    #   This code assumes one section per level+timeblock+subject
                    item = section_dict[section][0]
                    print ' -> Section %s (%d/%d) %s: Scores %d-%d' % (section, item[0].num_students(), item[1], item[0], item[0].min_score, item[0].max_score)
                """

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

        #dummy_anchor = self.program_anchor_cached().tree_create(['DummyClass'])
        #dummy_anchor.save()
        
        data = request.POST
        
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
                newclass.anchor = self.program.classes_node()
    
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
        
        #dummy_anchor.delete()
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

