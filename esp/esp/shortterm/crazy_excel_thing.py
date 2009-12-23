
from collections import defaultdict
from esp.survey.models import Answer, SurveyResponse, Survey
from esp.program.models import Program, ClassSubject
from datetime import datetime, date, time

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

import gc
import xlwt

# I want a defaultdict class in which default_factory
# takes the missing key as its argument, to generate a new value
class defaultdict_perkey(dict):
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not hasattr(default_factory, '__call__')):
            raise TypeError('first argument must be callable')
        dict.__init__(self, *a, **kw)
        self.default_factory = default_factory
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory(key)
        return value
    def copy(self):
        return self.__copy__()
    def __copy__(self):
        return type(self)(self.default_factory, self)
    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))
    def __repr__(self):
        return 'defaultdict_perkey(%s, %s)' % (self.default_factory,
                                        dict.__repr__(self))
        

def get_all_data():
    # Has to be a list so that each answer object is persistent,
    # since we're tacking data on
    all_answers = list( Answer.objects.all().select_related('anchor',
                                                            'anchor__parent',
#                                                            'anchor__parent__parent',
                                                            'question',
                                                            'question__questiontype',
#                                                            'question__anchor',
#                                                            'question__survey',
#                                                            'question__survey__anchor',
                                                            'survey_response',
                                                            'survey_response__survey',
#                                                            'survey_response__survey__anchor')
                                                            ) )

    gc.collect() # 'cause the Django query parser system uses gobs of RAM; keep RAM usage down a bit
    
    all_survey_responses = list( SurveyResponse.objects.all().select_related() )
    all_surveys = list( Survey.objects.all().select_related() )

    # This one can be an ordinary QuerySet; no funky tricks and small table
    all_programs = Program.objects.all().select_related()#'anchor__parent', 'anchor__parent__parent')

    # Bigger table; but it turns out we want real objects anyway so we need an ordinary QuerySet
    # In fact, we need even more fields; pull some stuff via catalog()
    # Don't bother using the cache for this; it doesn't fit.
    all_classes = ClassSubject.objects.catalog(None, use_cache=False)

    gc.collect()
    
    all_classes_dict = {}
    for c in all_classes:
        all_classes_dict[c.anchor_id] = c        

    all_programs_dict = {}
    for p in all_programs:
        all_programs_dict[p.anchor_id] = p

    all_surveys_dict = {}
    for s in all_surveys:
        s._responses = []
        s._questions = set()
        s._per_class_questions = set()
        all_surveys_dict[s.id] = s
        
    all_survey_responses_dict = {}
    for s in all_survey_responses:
        s._answers = list()
        all_survey_responses_dict[s.id] = s
        
    for a in all_answers:
        # Get the parent program
        # We could be a per-class question; figure this out from our anchor
        a._is_per_class = not(a.anchor_id in all_programs_dict)
        a._program = all_programs_dict[ ( a.anchor_id if not a._is_per_class else a.anchor.parent.parent_id ) ]
        a._program_name = a._program.niceName()

        if a._is_per_class:
            try:
                a._class = all_classes_dict[a.anchor_id]
            except KeyError:
                pass # Class doesn't turn up in the Catalog for some reason, despite being surveyable.  Ignore it.
        else:
            a._class = None

        s = all_survey_responses_dict[a.survey_response_id]
        s._answers.append(a)

        s = all_surveys_dict[a.survey_response.survey_id]
        if a._is_per_class:
            s._per_class_questions.add(a.question)
        else:
            s._questions.add(a.question)

    # Put the questions in survey-order
    for s in all_survey_responses:
        all_surveys_dict[s.survey_id]._responses.append(s)

    for s in all_surveys:
        s._questions = list(s._questions)
        s._questions.sort(key=lambda x: (x.seq, x.id))
        
    return all_surveys


def auto_cell_type(val):
#    print type(val),
    val = auto_cell_type_wrapped(val)
    print type(val)
#    return val

def auto_cell_type_wrapped(val):
    if isinstance(val, (datetime, date, time)):
        return val
    
    try:
        return int(val)
    except:
        pass

    try:
        return float(val)
    except:
        pass

    # Give up; not a type that Excel likes
    val = unicode(val)
    
    if val.upper() in ("TRUE", "FALSE", "T", "F"):
        if val.upper() in ("TRUE", "T"):
            return True
        else:
            return False

    # No idea; we'll just return a string
    return val
    

def write_xls_row(ws, rownum, data_list):

    # Styles yoinked from <http://www.djangosnippets.org/snippets/1151/>
    styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
              'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
              'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
              'default': xlwt.Style.default_style}
    
    row = ws.row(rownum)
    for c, d in enumerate(data_list):
        value = auto_cell_type(d)
        
        if isinstance(value, datetime):
            cell_style = styles['datetime']
        elif isinstance(value, date):
            cell_style = styles['date']
        elif isinstance(value, time):
            cell_style = styles['time']
        else:
            cell_style = styles['default']

        row.write(c, value, style=cell_style)

    return rownum + 1

#def write_answer_row(ws, row, ans):
#    data_list = [
#        ans.id,
#        ans._program_name,
#        ans._is_per_class,
#        ans._class.anchor.name if ans._class else "",
#        ans._class.anchor.friendly_name if ans._class else "",
#        ans._class.num_students(),
#        ans._class.pretty_teachers(),
#        ans.survey_response.id,
#        ans.survey_response.time_filled,
#        ans.survey_response.survey.name,
#        ans.survey_response.survey.category,
#        ans.question.
#        ans.answer(),
#        ]

def init_worksheet(workbook, sheet_name, default_cols):
    if len(sheet_name) > 31:
        sheet_name = sheet_name[:28] + "..."
    ws = workbook.add_sheet(sheet_name)
    write_xls_row(ws, 0, default_cols)
    return ws


def get_style(val):
    styles = { 'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
               'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
               'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
               'default': xlwt.Style.default_style }

    if isinstance(value, datetime):
        cell_style = styles['datetime']
    elif isinstance(value, datetime.date):
        cell_style = styles['date']
    elif isinstance(value, datetime.time):
        cell_style = styles['time']
    else:
        cell_style = styles['default']

    return cell_style




def build_workbook_data():
    all_surveys = get_all_data()

    workbook = xlwt.Workbook(encoding='utf-8', style_compression=2)
    default_column_names = ["Survey Response ID#", "'Survey Filed' timestamp", "Survey Name"]
    
    for s in all_surveys:
        this_column_names = []
        this_question_ids = []
        for q in s._questions:
            this_column_names.append("%s (%s; %s)" % (q.name, q.question_type.name, str(list(enumerate(q.param_values)))))
            this_question_ids.append(q.id)
        ws = init_worksheet(workbook, "%s (ALL %s) %s" % (s.id, s.category, s.name), default_column_names + this_column_names)

        row = 1
        for r in s._responses:
            surveyresponse_answers = [r.id, r.time_filled, s.name]

            ans_dict = defaultdict(str)

            for ans in r._answers:
                ans_dict[ans.question_id] = auto_cell_type(ans.answer)# if isinstance(ans.answer, (datetime, basestring, bool, int, long, float)) else unicode(ans.answer)

            this_answers = [ans_dict[q] for q in this_question_ids]
            
            write_xls_row(ws, row, surveyresponse_answers + this_answers)

            row += 1

        this_column_names = []
        this_question_ids = []
        for q in s._per_class_questions:
            this_column_names.append("%s (%s; %s)" % (q.name, q.question_type.name, str(list(enumerate(q.param_values)))))
            this_question_ids.append(q.id)
        ws = init_worksheet(workbook, "%s (PER-CLS %s) %s" % (s.id, s.category, s.name), default_column_names + this_column_names)

        response_per_usercls = defaultdict( lambda: defaultdict(list) )
        row = 1
        for r in s._responses:
            for ans in r._answers:
                response_per_usercls[r.id][ans.anchor_id].append(ans)

            surveyresponse_answers = [r.id, r.time_filled, s.name]
            
            for resp in response_per_usercls[r.id].values():
                ans_dict = defaultdict(str)

                for ans in resp:
                    ans_dict[ans.question_id] = auto_cell_type(ans.answer)# if isinstance(ans.answer, (datetime, basestring, bool, int, long, float)) else unicode(ans.answer)

                this_answers = [ans_dict[q] for q in this_question_ids]
                this_answers_filtered = [x for x in this_answers if x != ""]

                write_xls_row(ws, row, surveyresponse_answers + this_answers)

                row += 1

    output = StringIO()
    workbook.save(output)
    return output

def build_workbook():
    output = build_workbook_data()
    gc.collect()  # build_workbook_data throws around a ton of data, and a ton of variables.  Clean them up.
    return output
