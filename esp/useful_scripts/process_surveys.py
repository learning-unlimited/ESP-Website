
from collections import defaultdict
from esp.survey.models import Answer, SurveyResponse, Survey
from esp.program.models import Program, ClassSubject, ClassSection
from datetime import datetime, date, time

from django.contrib.contenttypes.models import ContentType

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

import gc
import xlwt

def get_all_data():
    """
    Get all survey data ever;
    then stuff it into variables hanging off of each survey in a list() of all Surveys in the db;
    then return that list of surveys
    """

    # Has to be a list so that each answer object is persistent,
    # since we're tacking data on
    # We *really really* want to get all relevant fields in a single query;
    # if we don't, the performance is absolutely horrible,
    # as there are (as of 12/2009) ~100,000 answers,
    # and 100,000 of any sort of query, no matter how cheap, takes an extremely long time.
    all_answers = list( Answer.objects.all().select_related('question',
                                                            'question__questiontype',
                                                            'survey_response',
                                                            'survey_response__survey',
                                                            ) )

    print 'Got answers'
    gc.collect() # 'cause the Django query parser system uses gobs of RAM; keep RAM usage down a bit

    all_survey_responses = list( SurveyResponse.objects.all().select_related() )
    all_surveys = list( Survey.objects.all().select_related() )

    print 'Got surveys/responses'
    gc.collect()

    # This one can be an ordinary QuerySet; no funky tricks and small table
    all_programs = Program.objects.all().select_related()#'anchor__parent', 'anchor__parent__parent')

    # Bigger table; but it turns out we want real objects anyway so we need an ordinary QuerySet
    # In fact, we need even more fields; pull some stuff via catalog()
    # Don't bother using the cache for this; it doesn't fit.
    all_classes = ClassSubject.objects.catalog(None, force_all=True, use_cache=False)

    print 'Got classes'
    gc.collect()

    all_sections = ClassSection.objects.all()

    print 'Got sections'
    gc.collect()

    content_type_program = ContentType.objects.get_for_model(Program)
    content_type_classsubject = ContentType.objects.get_for_model(ClassSubject)
    content_type_classsection = ContentType.objects.get_for_model(ClassSection)

    # So, we now basically have a tree structure, with Answers at the leaves
    # and Surveys at the root.
    # Join this tree structure together in memory.

    # Survey responses for a class share an anchor with that class
    all_classes_dict = {}
    for c in all_classes:
        all_classes_dict[c.id] = c

    all_sections_dict = {}
    for s in all_sections:
        all_sections_dict[s.id] = s

    # Survey responses for a program share an anchor with that program
    all_programs_dict = {}
    for p in all_programs:
        all_programs_dict[p.id] = p

    # Prepare the survey and survey_response lists to receive a whole pile of data
    # aggregated from the massive Answers query above
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

    # Iterate through all answers ever.
    # Build the tree of data from the leaves up,
    # aggregating redundant data from the Answers using sets and dictionaries.
    for a in all_answers:
        # Get the parent program
        # We could be a per-class question; figure this out from our anchor
        a._is_per_section = (a.content_type == content_type_classsection)
        a._is_per_class = (a.content_type == content_type_classsubject)

        if a._is_per_class:
            a._class = all_classes_dict[a.object_id]
            a._program = all_programs_dict[a._class.parent_program_id]
            a._section = None
        elif a._is_per_section:
            a._section = all_sections_dict[a.object_id]
            a._class = all_classes_dict[a._section.parent_class_id]
            a._program = all_programs_dict[a._class.parent_program_id]
        else:
            a._program = all_programs_dict[a.object_id]
            a._class = None
            a._section = None

        a._program_name = a._program.niceName()

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

    # And, finally, return the survey data
    return all_surveys

def auto_cell_type(val):
    """
    Excel supports a variety of Python data types.
    Given 'val' as possibly a proper type, possibly a string that
    could be converted to the proper type, and possibly something else,
    try to output The Right Thing(tm).
    """

    # We're not smart about datetime's.
    # If we have one, just throw it back to Excel; it can deal with them properly.
    if isinstance(val, (datetime, date, time)):
        return val

    # Are we an int?
    try:
        return int(val)
    except:
        pass

    # Are we a float?
    try:
        return float(val)
    except:
        pass

    # Give up; not a type that Excel likes
    val = unicode(val)

    # Are we something that looks like a boolean?
    if val.upper() in ("TRUE", "FALSE", "T", "F"):
        if val.upper() in ("TRUE", "T"):
            return True
        else:
            return False

    # No idea; we'll just return a string
    # Excel can deal with Unicode, so leave it as a Unicode-string.
    return val


def write_xls_row(ws, rownum, data_list):
    """
    Given a list representing the contents of a row,
    the index of a row in an Excel Worksheet,
    and an Excel Worksheet object.
    write the row.

    Try to be smart about data types and cell formats and whatnot.
    This will probably need tweaking someday.

    Does not check for overwriting; if your worksheet is configured to
    not permit overwriting already-written cells, this code can fail as a result
    if not used accordingly.

    Also, this code tends to set a lot of redundant styles on cells,
    so you're strongly recommended to configure your workbook to use style compression.
    """
    # Styles yoinked from <http://www.djangosnippets.org/snippets/1151/>
    styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
              'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
              'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
              'default': xlwt.Style.default_style}

    # Go get the row object for the row in question
    row = ws.row(rownum)
    for c, d in enumerate(data_list):
        value = auto_cell_type(d)

        # Do some magic to guess the style
        # Excel's default style for date/time-like things is really bad
        # (just print the number in Windows date format, float(days) )
        # but its other defaults are sane, so try to catch and convert dates
        if isinstance(value, datetime):
            cell_style = styles['datetime']
        elif isinstance(value, date):
            cell_style = styles['date']
        elif isinstance(value, time):
            cell_style = styles['time']
        else:
            cell_style = styles['default']

        # Actually write the row
        row.write(c, value, style=cell_style)

    # Return the row number of the next row.
    # Possibly useful for iteration over workbook?
    return rownum + 1


def init_worksheet(workbook, sheet_name, default_cols):
    """
    Helper method.
    Given a workbook, the title for a sheet, and the column headers,
    create the workbook and populate it with the specified name and column headers.
    If the name is longer than the legal limit (31 characters), truncate it to
    28 characters + "...".
    We should probably also do something spiffy with illegal characters in the name,
    as Excel has a lot of them; but we don't; we just hand them off to the workbook
    and let it throw an error or something.
    """
    if len(sheet_name) > 31:
        sheet_name = sheet_name[:28] + "..."
    ws = workbook.add_sheet(sheet_name)
    write_xls_row(ws, 0, default_cols)
    return ws


def build_workbook_data():
    """
    Return a StringIO object containing the binary data of a Microsoft Excel .xls file,
    containing all survey results for every program ever.
    """
    # Get enormous gobs of data
    all_surveys = get_all_data()

    # Make us a workbook
    workbook = xlwt.Workbook(encoding='utf-8', style_compression=2)

    # These columns are in every spreadsheet
    default_column_names = ["Survey Response ID#", "'Survey Filed' timestamp", "Survey Name"]

    # Iterate through all surveys
    for s in all_surveys:
        # It ends up being really ugly to put responses to whole-program and per-class questions
        # all in the same worksheet.
        # So, don't.
        # Build two worksheets, one for ALL (whole-program) questions and one for PER-CLS questions.

        # ALL:
        this_column_names = []
        this_question_ids = []
        for q in s._questions:
            # Grab the names of questions that we care about
            this_column_names.append("%s (%s; %s)" % (q.name, q.question_type.name, str(list(enumerate(q.param_values)))))
            # And grab the corresponding question-ID's in order, so that we can sort answers accordingly
            this_question_ids.append(q.id)

        # Actually go ahead and make the worksheet
        ws = init_worksheet(workbook, "%s (ALL %s) %s" % (s.id, s.category, s.name), default_column_names + this_column_names)

        row = 1
        # Iterate through all responses, output one row apiece
        for r in s._responses:

            # Values for stock columns
            surveyresponse_answers = [r.id, r.time_filled, s.name]

            ans_dict = defaultdict(str)

            # Build up a dictionary mapping questions to answers, for just this survey response
            for ans in r._answers:
                ans_dict[ans.question_id] = auto_cell_type(ans.answer)

            # Go build up a list of the answer to each question that we care about.
            # Because ans_dict is a defaultdict(str), if we ask for an answer that we don't have,
            # we'll just get "", which is probably what we want.
            this_answers = [ans_dict[q] for q in this_question_ids]

            write_xls_row(ws, row, surveyresponse_answers + this_answers)

            row += 1

        # PER-CLS:
        this_column_names = ["Class ID", "Section Number", "Teachers"]
        this_question_ids = [-1, -2, -3]

        # Iterate through per-class questions this time
        for q in s._per_class_questions:
            # But build up the same data structures
            this_column_names.append("%s (%s; %s)" % (q.name, q.question_type.name, str(list(enumerate(q.param_values)))))
            this_question_ids.append(q.id)
        ws = init_worksheet(workbook, "%s (PER-CLS %s) %s" % (s.id, s.category, s.name), default_column_names + this_column_names)

        # Now we have to do something tricky,
        # because we don't have one response per row;
        # we have one row per response per class.
        response_per_usercls = defaultdict( lambda: defaultdict(list) )
        row = 1
        for r in s._responses:
            # Build up a data structure giving answers per response per class
            for ans in r._answers:
                response_per_usercls[r.id][ans.object_id].append(ans)

            surveyresponse_answers = [r.id, r.time_filled, s.name]

            # And output data for each one of them
            for resp in response_per_usercls[r.id].values():
                ans_dict = defaultdict(str)

                for ans in resp:
                    ans_dict[ans.question_id] = auto_cell_type(ans.answer)
                    ans_dict[-1] = ans._class.emailcode() if ans._class != None else ans_dict[-1]
                    ans_dict[-2] = ans._section.title() if ans._section != None else ans_dict[-2]
                    ans_dict[-3] = ", ".join("%s %s" % (x.first_name, x.last_name) for x in ans._class._teachers) if ans._class != None else ans_dict[-3]

                this_answers = [ans_dict[q] for q in this_question_ids]

                # If we actually have any data; ie., we're not about to print out the empty string
                if not reduce(lambda comb, val: comb and (val == ""), this_answers, True):
                    write_xls_row(ws, row, surveyresponse_answers + this_answers)
                    row += 1

    # Output to a StringIO instance, so that we can work with the data in memory some more.
    # It turns out that xlwt is much more efficient than Django, at storing data in-memory;
    # so this isn't completely horrible.
    output = StringIO()
    workbook.save(output)
    return output


def build_workbook():
    """
    Return a StringIO object containing the binary data of a Microsoft Excel .xls file,
    containing all survey results for every program ever.
    """
    output = build_workbook_data()
    gc.collect()  # build_workbook_data throws around a ton of data, and a ton of variables.  Clean them up.
    return output
