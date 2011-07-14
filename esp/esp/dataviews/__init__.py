from esp.program.models import *
from esp.users.models import * 
from esp.cal.models import * 
from esp.survey.models import *
from esp.datatree.models import DataTree
from django.db.models import Model
from django.db.models.related import RelatedObject
from django.db.models.fields.related import RelatedField, ManyToManyField
from inspect import isclass
from django.db.models.sql.constants import QUERY_TERMS, LOOKUP_SEP

useful_models = [User, ESPUser, Program, RegistrationProfile, RegistrationType, StudentAppQuestion, StudentAppResponse, StudentAppReview, StudentApplication, StudentRegistration, Event, ClassCategories, ClassSection, ClassSubject, EventType, ArchiveClass, FinancialAidRequest, QuestionType, Question, SurveyResponse, Survey, ContactInfo, EducatorInfo, GuardianInfo, K12School, StudentInfo, TeacherInfo, UserAvailability, UserBit, ZipCodeSearches, ZipCode]
query_terms = QUERY_TERMS.keys()

def path_v1(*args):
    '''
Finds a path from args[0] to args[1], or returns [] if they aren't related in the forward direction.

If they are both models, returns a list of strings, which represent valid field lookup paths that can filter the first based on the second. For example, path_v1(StudentRegistration, User) would return ['user'], and path_v1(StudentRegistration, ClassSubject) would return ['section__parent_class'].

If the first is a model and the second is an instance, a filter is applied to the model, subject to the constaint of the instance. Roughly, this means that path_v1(model, instance)[i] is equivalent to model.objects.filter(path_v1(model, type(instance))[i]=instance).

If the first is an instance and the second is a model, the function returns the instance of the model that is linked to the given instance. For example, path_v1(sr, User) would return sr.user, and path_v1(sr, ClassSubject) would return sr.section.parent_class (where sr is an instance of StudentRegistration).
    '''
    if 2 != len(args):
        raise TypeError("path_v1 expected 2 arguments, got "+str(len(args)))
    instances = [None for i in range(2)]
    classes = [None for i in range(2)]
    for i in range(2):
        if (not (isclass(args[i]) and issubclass(args[i], Model))) and (not isinstance(args[i], Model)): 
            raise TypeError("path_v1 argument "+str(i+1)+" must be a model or an instance of a model")
        if isclass(args[i]):
            classes[i] = args[i]
        else:
            instances[i] = args[i]
            classes[i] = type(args[i])
    if instances[0] and instances[1]:
        raise TypeError("at least one of the path_v1 arguments must be a model")
    stack = [(classes[0],())]
    paths = []
    while stack:
        (model, path) = stack.pop()
        if issubclass(model, DataTree):
            continue
        relatedObjects = {}
        if issubclass(model, classes[1]):
            paths.append(path)
        for name, field in model._meta.init_name_map().iteritems():
            if not isinstance(field[0], RelatedObject) and not isinstance(field[0], ManyToManyField):
                if isinstance(field[0], RelatedField):
                    stack.append((field[0].rel.to, path+(name,)))
            else:
                relatedObjects[name] = field
    results = [None for i in range(len(paths))]
    if instances[0]:
        for i in range(len(paths)):
            obj = instances[0]
            for attr in paths[i]:
                obj = getattr(obj, attr)
            results[i] = obj
    elif instances[1] and not instances[0]:
        results = [classes[0].objects.filter(**{LOOKUP_SEP.join(path): instances[1]}) for path in paths if path]
        if not paths[0]:
            results += [instances[1]]
    else:
        results = [LOOKUP_SEP.join(path) for path in paths]
    return results

def path_v2(model, *conditions):
    '''
Returns a filter of all objects of type model, subject to the list of conditions. 

The first argument, model, must be a model. It cannot be an instance of a model, or any other object.

The list of conditions can be arbitrarily long, but must consist entirely of instances of models.

The function uses path_v1() to find the forward path from model to conditions[i] (for all i), and then applies the appropriate filter.

If there is more than one path from model to conditions[i], the function asks the user (via the raw_input() function) which path(s) to filter on.
    '''
    if not (isclass(model) and issubclass(model, Model)):
        raise TypeError("path_v2 argument 1 must be a model")
    if not len(conditions):
        return model.objects.all()
    models = [None for i in range(len(conditions))]
    for i in range(len(conditions)):
        if not isinstance(conditions[i], Model): 
            raise TypeError("path_v2 argument 2 must be a list of instances of models")
        elif isinstance(conditions[i], model):
            raise TypeError("path_v2 argument 2 must not contain any instances of argument 1")
        models[i] = type(conditions[i])
    kwargs = {}
    paths = None
    repeat = None
    use = None
    for i in range(len(conditions)):
        paths = path_v1(model, models[i])
        for path in paths: 
            repeat = True
            while repeat:
                use = raw_input("Include the path "+path+" as a condition ([y]/n)? ")
                repeat = False
                if use.lower() == 'y' or use.lower() == 'yes' or not use: 
                    kwargs[path] = conditions[i]
                elif not (use.lower() == 'n' or use.lower() == 'no'):
                    repeat = True
    return model.objects.filter(**kwargs)

def iscorrecttuple(T): 
    if not ((isinstance(T, tuple)) and (3 <= len(T) <= 4)):
        return False
    elif not (isclass(T[0]) and issubclass(T[0], Model)):
        return False
    elif not (isinstance(T[1], str) and T[1] in T[0]._meta.init_name_map().keys()):
        return False
    elif len(T) == 3:
        try: 
            T[0]._meta.init_name_map()[T[1]][0].to_python(T[2])
        except Exception:
            return False
        else: 
            return True
    elif len(T) == 4:
        if not T[2] in query_terms:
            return False
        else:
            return True
    else:
        return False
    
def path_v3(model, *conditions):
    '''
Returns a filter of all objects of type model, subject to the list of conditions. 

The first argument, model, must be a model. It cannot be an instance of a model, or any other object.

The list of conditions can be arbitrarily long, but each condition must be one of the following: 
 * an instance of a model 
 * a 3-tuple (model, field, value), where field is a string which is the name of a field of model, and value is a valid value of that field

The function uses path_v1() to find the forward path from model to conditions[i] or conditions[i][0] (for all i), and then applies the appropriate filter.

The function asks the user (via the raw_input() function) which path(s) to filter on.
    '''
    conditions = list(conditions)
    if not (isclass(model) and issubclass(model, Model)):
        raise TypeError("path_v3 argument 1 must be a model")
    iter_conditions = range(len(conditions))
    models = [None for i in iter_conditions]
    fields = ['' for i in iter_conditions]
    values = [None for i in iter_conditions]
    for i in iter_conditions: 
        if isinstance(conditions[i], tuple) and isinstance(conditions[i][-1], Model): 
            conditions[i] = conditions[i][-1]
        if isinstance(conditions[i], Model): 
            if isinstance(conditions[i], model):
                raise TypeError("path_v3 argument 2 must not contain any instances of argument 1")
            values[i] = conditions[i]
            models[i] = type(conditions[i])
        elif isinstance(conditions[i], tuple) and len(conditions[i]) == 3 and iscorrecttuple(conditions[i]):
            fields[i] = conditions[i][1]
            values[i] = conditions[i][2]
            models[i] = conditions[i][0]
        else:
            raise TypeError("path_v3 argument 2 must be a list, with each item being either an instance of a model or valid (model, field, value) 3-tuple")
    
    repeat = False
    use = ''
    kwargs = {}
    paths = []
    num_paths = 0
    for i in iter_conditions:
        for path in [LOOKUP_SEP.join((path, fields[i])).strip(LOOKUP_SEP) for path in path_v1(model, models[i])]: 
            repeat = True
            while repeat:
                use = raw_input("Include the path "+path+" as a condition ([y]/n)? ")
                repeat = False
                if use.lower() == 'y' or use.lower() == 'yes' or not use: 
                    kwargs[path] = values[i]
                elif not (use.lower() == 'n' or use.lower() == 'no'):
                    repeat = True
    return model.objects.filter(**kwargs)

def path_v4(model, *conditions):
    '''
Returns a filter of all objects of type model, subject to the list of conditions. 

The first argument, model, must be a model. It cannot be an instance of a model, or any other object.

The list of conditions can be arbitrarily long, but each condition must be one of the following: 
 * an instance of a model 
 * a 3-tuple (model, field, value), where field is a string which is the name of a field of model, and value is a valid value of that field
 * a 4-tuple (model, field, query_term, value), where field is a string which is the name of a field of model, query_term is a string which is the name of a Django query term (defined in django.db.models.sql.constants.QUERY_TERMS), and value is a valid value of that field

The function uses path_v1() to find the forward path from model to conditions[i] or conditions[i][0] (for all i), and then applies the appropriate filter.

The function asks the user (via the raw_input() function) which path(s) to filter on.
    '''
    conditions = list(conditions)
    if not (isclass(model) and issubclass(model, Model)):
        raise TypeError("path_v4 argument 1 must be a model")
    iter_conditions = range(len(conditions))
    models = [None for i in iter_conditions]
    fields = ['' for i in iter_conditions]
    lookup_type = ['' for i in iter_conditions]
    values = [None for i in iter_conditions]
    for i in iter_conditions: 
        if isinstance(conditions[i], tuple) and isinstance(conditions[i][-1], Model): 
            conditions[i] = conditions[i][-1]
        if isinstance(conditions[i], Model): 
            if isinstance(conditions[i], model):
                raise TypeError("path_v4 argument 2 must not contain any instances of argument 1")
            values[i] = conditions[i]
            models[i] = type(conditions[i])
        elif isinstance(conditions[i], tuple) and iscorrecttuple(conditions[i]):
            fields[i] = conditions[i][1]
            models[i] = conditions[i][0]
            if len(conditions[i]) == 3:
                values[i] = conditions[i][2]
            else:
                values[i] = conditions[i][3]
                lookup_type[i] = conditions[i][2]
        else:
            raise TypeError("path_v4 argument 2 must be a list, with each item being either an instance of a model or valid (model, field, value) 3-tuple")
    
    repeat = False
    use = ''
    kwargs = {}
    paths = []
    num_paths = 0
    for i in iter_conditions:
        for path in [LOOKUP_SEP.join((path, fields[i], lookup_type[i])).strip(LOOKUP_SEP) for path in path_v1(model, models[i])]: 
            repeat = True
            while repeat:
                use = raw_input("Include the path "+path+" as a condition ([y]/n)? ")
                repeat = False
                if use.lower() == 'y' or use.lower() == 'yes' or not use: 
                    kwargs[path] = values[i]
                elif not (use.lower() == 'n' or use.lower() == 'no'):
                    repeat = True
    return model.objects.filter(**kwargs)
