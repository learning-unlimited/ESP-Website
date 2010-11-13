""" Automatic lunch constraint generator
    Michael Price (price@kilentra.net)
"""
"""
#   Stuff specific to Stanford Splash Fall 2010 (Saturday)
program_id = 12
morning_ids = [78, 80]
lunch_ids = [81, 82]
afternoon_ids = [83, 84, 85, 99]
#   End of stuff specific to Splash Fall 2010 (Saturday)
"""

#   Stuff specific to Stanford Splash Fall 2010 (Sunday)
program_id = 12
morning_ids = [87, 88]
lunch_ids = [89, 90]
afternoon_ids = [93, 94, 95, 96]
#   End of stuff specific to Splash Fall 2010 (Sunday)


ON_FAILURE_CODE = """
# This code is part of a function: on_failure(schedule_map)
# The function should return a tuple containing the new schedule
# map as its first element.  (Messages provided in the second
# element are ignored since the default error handling was deemed
# sufficient, but this can be changed by uncommenting some code.)

# Application specific: IDs of lunch periods for this constraint
lunch_choices = %s

# Compute list of feasible options for student's lunch period
availability = [(len(schedule_map.map[x]) == 0) for x in lunch_choices]
time_options = []
for i in range(len(lunch_choices)):
    if availability[i]: time_options.append(lunch_choices[i])

# Choose a lunch period, find classes in available times
if len(time_options) == 0:
    return (schedule_map, 'Unable to autoschedule lunch.')
else:
    dest_sec = None
    dest_qs = ClassSection.objects.filter(meeting_times__id__in=time_options, parent_class__category__category='Lunch')
    if dest_qs.count() == 0:
        return (schedule_map, 'Unable to autoschedule lunch.')
    elif dest_qs.count() == 1:
        dest_sec = dest_qs[0]
    else:
        dest_sec = random.choice(list(dest_qs))
    rets = dest_sec.preregister_student(schedule_map.user, overridefull=True)
    schedule_map.add_section(dest_sec)
    data = str(schedule_map.map)
    return (schedule_map, data)
""" % lunch_ids

def apply_binary_op_to_list(expression, operator_text, identity_value, tokens):
    """ Add the appropriate boolean tokens to 'expression' so
        that the operator in 'operator_text' is applied over all
        items in 'tokens'
    """
    
    #   If there are 0 tokens in the list, do nothing
    if len(tokens) == 0:
        pass
    #   If there is 1 token in the list, apply the operator to it and the identity.
    elif len(tokens) == 1:
        expression.add_token(tokens.pop())
        expression.add_token(identity_value)
        expression.add_token(operator_text)
    #   If there are 2 tokens in the list, apply the operator to those tokens.
    elif len(tokens) == 2:
        expression.add_token(tokens.pop())
        expression.add_token(tokens.pop())
        expression.add_token(operator_text)
    #   If there are more than 2 tokens in the list, divide the list in half and work recursively
    else:
        midpoint = len(tokens) / 2
        first_half = tokens[:midpoint]
        second_half = tokens[midpoint:]
        apply_binary_op_to_list(expression, operator_text, identity_value, first_half)
        apply_binary_op_to_list(expression, operator_text, identity_value, second_half)
        expression.add_token(operator_text)
        
    return expression

def setup_lunch_constraint(program_id, morning_ids, lunch_ids, afternoon_ids):
    """ Set up lunch constraints as follows:
        IF      (student has any morning classes)
            AND (student has any afternoon classes)
        THEN    (student must have a "lunch" period)
    """
    from esp.program.models import Program, BooleanExpression, ScheduleConstraint, ScheduleTestOccupied, ScheduleTestCategory, ClassCategories
    
    prog = Program.objects.get(id=program_id)
    
    #   Prepare empty expression objects
    exp_requirement = BooleanExpression()
    exp_requirement.label = 'Choose a lunch period at either 12pm or 1pm'
    exp_requirement.save()
    
    exp_check = BooleanExpression()
    exp_check.label = '%s automatically generated check' % prog.niceName()
    exp_check.save()
    
    constraint = ScheduleConstraint()
    constraint.program = prog
    constraint.condition = exp_check
    constraint.requirement = exp_requirement
    constraint.on_failure = ON_FAILURE_CODE
    constraint.save()
    
    #   Build schedule tests for each period, but don't save all them;
    #   they are saved in the correct order by apply_binary_op_to_list()
    seq_id = 0
    morning_tests = []
    for timeblock_id in morning_ids:
        new_test = ScheduleTestOccupied()
        new_test.timeblock_id = timeblock_id
        new_test.exp_id = exp_check.id
        morning_tests.append(new_test)
        seq_id += 1
    apply_binary_op_to_list(exp_check, 'OR', '0', morning_tests)
    
    lunch_tests = []
    for timeblock_id in lunch_ids:
        new_test = ScheduleTestCategory()
        new_test.timeblock_id = timeblock_id
        new_test.exp_id = exp_requirement.id
        lunch_category, created = ClassCategories.objects.get_or_create(category='Lunch')
        new_test.category = lunch_category
        lunch_tests.append(new_test)
        seq_id += 1
    apply_binary_op_to_list(exp_requirement, 'OR', '0', lunch_tests)
    
    afternoon_tests = []
    for timeblock_id in afternoon_ids:
        new_test = ScheduleTestOccupied()
        new_test.timeblock_id = timeblock_id
        new_test.exp_id = exp_check.id
        afternoon_tests.append(new_test)
        seq_id += 1
    apply_binary_op_to_list(exp_check, 'OR', '0', afternoon_tests)
    
    #   Add an AND to the exp_check so that it requires both a morning class and an afternoon class
    exp_check.add_token('AND')
    
    return constraint
    
    
if __name__ == '__main__':
    from esp.program.models import *
    from esp.cal.models import *
    
    prog = Program.objects.get(id=program_id)
    """
    #   Ensure that there is a "Lunch" category
    category, created = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
    print 'Found category: %s' % category
    
    #   Ensure that there is at least one "Lunch" class in the program
    lunch_subjects = ClassSubject.objects.filter(parent_program__id=program_id, category__category='Lunch')
    lunch_subject = None
    if lunch_subjects.count() == 0:
        new_subject = ClassSubject()
        new_subject.grade_min = 7
        new_subject.grade_max = 12
        new_subject.parent_program = prog
        new_subject.category = category
        new_subject.class_info = 'Enjoy a break for lunch with your friends!  Please register for at least one lunch period.'
        new_subject.class_size_min = 0
        new_subject.class_size_max = 1000
        new_subject.status = 10
        new_subject.anchor = prog.classes_node()
        new_subject.save()
        nodestring = new_subject.category.symbol + str(new_subject.id)
        new_anchor = new_subject.anchor.tree_create([nodestring])
        new_anchor.friendly_name = 'Lunch Period'
        new_anchor.save()
        new_subject.anchor = new_anchor
        new_subject.save()
        lunch_subject = new_subject
        print 'Generated subject: %s' % lunch_subject
    else:
        lunch_subject = lunch_subjects[0]
        print 'Selected subject: %s' % lunch_subject
    
    #   Ensure that there is at least one class section in each lunch period and that they are all approved
    for ts_id in lunch_ids:
        event = Event.objects.get(id=ts_id)
        lunch_sections = lunch_subject.sections.filter(meeting_times__id=ts_id)
        if lunch_sections.count() == 0:
            new_section = lunch_subject.add_section(status=10)
            new_section.meeting_times.add(ts_id)
            print 'Generated section for %s: %s' % (event, new_section)
        else:
            for sec in lunch_sections:
                sec.status = 10
                sec.save()
                print 'Approved section for %s: %s' % (event, sec)
    """            
    #   Generate schedule constraint
    print 'Generated constraint: %s' % setup_lunch_constraint(program_id, morning_ids, lunch_ids, afternoon_ids)
