from esp.program.models import *
from esp.users.models import * 
from esp.cal.models import * 
from esp.survey.models import *
from django.db.models import Model
from django.db.models.related import RelatedObject
from django.db.models.fields.related import RelatedField, ForeignKey, ManyToManyField
from django.db.models.sql.constants import QUERY_TERMS, LOOKUP_SEP
from django.forms.forms import pretty_name
from django.utils.safestring import mark_safe
from inspect import isclass
from collections import deque
from datetime import datetime

useful_models = sorted([ESPUser, Program, RegistrationProfile, RegistrationType, StudentAppQuestion, StudentAppResponse, StudentAppReview, StudentApplication, StudentRegistration, Event, ClassCategories, ClassSection, ClassSubject, EventType, ArchiveClass, FinancialAidRequest, QuestionType, Question, SurveyResponse, Survey, ContactInfo, EducatorInfo, GuardianInfo, K12School, StudentInfo, TeacherInfo, UserAvailability, ZipCodeSearches, ZipCode], key=lambda model: model.__name__)
query_terms = ('exact', 'iexact', 'contains', 'icontains', 'gt', 'gte', 'lt', 'lte', 'in', 'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'year', 'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex', )

def is_useful_model(cls): 
    is_useful_model = False
    if isclass(cls) and issubclass(cls, Model): 
        for model in useful_models:
            if issubclass(cls, model): 
                is_useful_model = True
                break
    return is_useful_model


def next_model(field, model = None): 
    if not isinstance(field, (RelatedField, RelatedObject, basestring)):
        raise TypeError("next_model argument 1 must be either a RelatedField, a RelatedObject, or a string")
    elif isinstance(field, basestring) and not is_useful_model(model): 
        raise TypeError("next_model argument 2 must be a useful model")
    elif isinstance(field, basestring) and is_useful_model(model) and not field in model._meta.init_name_map().keys(): 
        raise TypeError("when next_model argument 1 is a string, next_model argument 2 must be a useful model with it as a field name")
    elif isinstance(field, basestring) and is_useful_model(model) and field in model._meta.init_name_map().keys(): 
        field = model._meta.init_name_map()[field][0]
    if isinstance(field, RelatedField):
        return field.rel.to
    elif isinstance(field, RelatedObject):
        return field.field.model

def path_v1(begin, end):
    '''
Finds a path from begin to end, or returns [] if they aren't related.

Returns a list of strings, which represent valid field lookup paths that can filter the first based on the second. For example, path_v1(StudentRegistration, User) would return ['user'], and path_v1(StudentRegistration, ClassSubject) would return ['section__parent_class']. 
    '''
    global useful_models
    classes = [begin, end]
    for (i,cls) in enumerate(classes): 
        if not is_useful_model(cls):
            raise TypeError("path_v1 argument "+str(i+1)+" must be a useful model")
    queue = deque([((),(begin,),False,set())])
    paths = []
    while queue:
        (path, models, many, visited) = queue.popleft()
        model = models[-1]
        if issubclass(model, end):
            paths.append((path, models, many))
            continue
        if model in visited or not (model in useful_models):
            continue
        for name, field in model._meta.init_name_map().iteritems():
            field = field[0]
            if not isinstance(field, (RelatedField, RelatedObject)):
                continue
            new_model = None
            new_many = many | False
            new_visited = set(visited)
            new_visited.add(model)
            if isinstance(field, (ManyToManyField, RelatedObject)):
                new_many = True
            new_model = next_model(field, model)
            queue.append((path+(name,), models+(new_model,), new_many, new_visited))
    # return [(LOOKUP_SEP.join(path), models, many) for (path,models,many) in paths][:max_paths]
    return paths

def label_for_path(base_model, path, models, many, field='', links=False): 
    label = label_for_model(base_model, links=True)
    if path: 
        for i,n in enumerate(path): 
            basic_n = u''.join(pretty_name(n).split()).lower()
            basic_modelname = u''.join(pretty_name(models[i+1].__name__).split()).lower()
            if unicode(n).lower() == unicode(models[i+1].__name__).lower(): 
                label += u' \u2192 ' + label_for_model(models[i+1], links=links)
            elif basic_n == basic_modelname or basic_n in basic_modelname or basic_modelname in basic_n:
                label += u' \u2192 ' + label_for_model(models[i+1], name=pretty_name(n), links=links)
            else: 
                label += u' \u2192 ' + label_for_model(models[i], name=pretty_name(n), h=n, links=links) + u' (' + label_for_model(models[i+1], links=links) + u')'
    if field:
        label += u' \u2192 ' + label_for_model(models[-1], name=pretty_name(field), h=field, links=links)
    return mark_safe(label)

def label_for_model(model, name=u'', h=u'', links=False): 
    label = u''
    if name: 
        label += unicode(name)
    else: 
        label += unicode(model.__name__)
    if h: 
        h = u'#%s' % h
    if links: 
        return mark_safe(u'<a href="/dataviews/%s/%s" target="_blank">%s</a>' % (model.__name__, h, label))
    else: 
        return label

def many_to_one_path(begin, end):
    '''
Finds a path from begin to end, using only forward ForeignKey relationships, or returns [] if they aren't related in this way.

Returns a list of strings, which represent valid field lookup paths that can filter the first based on the second. For example, many_to_one_path(StudentRegistration, User) would return ['user'], and many_to_one_path(StudentRegistration, ClassSubject) would return ['section__parent_class']. 
    '''
    global useful_models
    classes = [begin, end]
    for (i,cls) in enumerate(classes): 
        is_useful_model = False
        if isclass(cls) and issubclass(cls, Model): 
            for model in useful_models:
                if issubclass(cls, model): 
                    is_useful_model = True
                    break
        if not is_useful_model:
            raise TypeError("many_to_one_path argument "+str(i+1)+" must be a useful model")
    queue = deque([((),(begin,),False,set())])
    paths = []
    while queue:
        (path, models, visited) = queue.popleft()
        model = models[-1]
        if issubclass(model, end):
            paths.append((path, models))
            continue
        if model in visited or not (model in useful_models):
            continue
        for name, field in model._meta.init_name_map().iteritems():
            if not isinstance(field[0], ForeignKey):
                continue
            new_model = None
            new_visited = set(visited)
            new_visited.add(model)
            new_model = field[0].rel.to
            queue.append((path+(name,), models+(new_model,), new_visited))
    return paths

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
        for (path, _, _) in paths: 
            repeat = True
            path = LOOKUP_SEP.join(path)
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
        for path in [LOOKUP_SEP.join(path+(fields[i],)).strip(LOOKUP_SEP) for (path,_,_) in path_v1(model, models[i])]: 
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
        for path in [LOOKUP_SEP.join(path+(fields[i],)).strip(LOOKUP_SEP) for (path,_,_) in path_v1(model, models[i])]: 
            repeat = True
            while repeat:
                use = raw_input("Include the path "+path+" as a condition ([y]/n)? ")
                repeat = False
                if use.lower() == 'y' or use.lower() == 'yes' or not use: 
                    kwargs[path] = values[i]
                elif not (use.lower() == 'n' or use.lower() == 'no'):
                    repeat = True
    return model.objects.filter(**kwargs)

def path_v5(model, paths, *conditions):
    '''
Returns a filter of all objects of type model, subject to the list of conditions. 

The first argument, model, must be a model. It cannot be an instance of a model, or any other object.

The second argument, paths, is a dictionary. paths[condition_model] is a list of selected paths from model to condition_model that should be queried.

The list of conditions can be arbitrarily long, but each condition must be one of the following: 
 * an instance of a model 
 * a 3-tuple (model, field, value), where field is a string which is the name of a field of model, and value is a valid value of that field
 * a 4-tuple (model, field, query_term, value), where field is a string which is the name of a field of model, query_term is a string which is the name of a Django query term (defined in django.db.models.sql.constants.QUERY_TERMS), and value is a valid value of that field

path_v1() is used outside of the scope of this function, to determine paths. Then path_v5 applies the appropriate filter.
    '''
    conditions = list(conditions)
    if not is_useful_model(model): 
        raise TypeError("path_v5 argument 1 must be a useful model")
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
                raise TypeError("path_v5 argument 3 must not contain any instances of argument 1")
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
            raise TypeError("path_v5 argument 3 must be a list, with each item being either an instance of a model or valid (model, field, value) 3-tuple")
    
    repeat = False
    use = ''
    kwargs = {}
    all_paths = []
    for i in iter_conditions:
        for path in paths[models[i]]: 
            kwargs[LOOKUP_SEP.join((path, fields[i], lookup_type[i])).strip(LOOKUP_SEP)] = values[i]
            all_paths.append(path)
    automatic_conditions_for_registrations = []
    for path in all_paths:
        new_path = passes_through(model, path, StudentRegistration, 'end_date')
        if new_path and isinstance(new_path, basestring):
            automatic_conditions_for_registrations.append(new_path)
    for condition in automatic_conditions_for_registrations: 
        condition_being_used = False
        for path in all_paths:
            if condition in path: 
                condition_being_used = True
                break
        if not condition_being_used: 
            kwargs[condition + LOOKUP_SEP + 'gte'] = datetime.now()
    return model.objects.filter(**kwargs).distinct()

def passes_through(base_model, path, target, addition = ''): 
    if not path: 
        return False
    if base_model == target and addition: 
        return addition
    elif base_model == target and not addition: 
        return True
    steps = path.split(LOOKUP_SEP)
    model = base_model
    new_path = ()
    for step in steps: 
        model = next_model(step, model)
        new_path += (step,)
        if model == target:
            return LOOKUP_SEP.join(new_path + (addition,))
    return ''

