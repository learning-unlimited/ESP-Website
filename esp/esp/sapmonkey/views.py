from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseServerError

from esp.program.models import Program, ClassSubject
from esp.users.models import admin_required, ESPUser

import gdata.gauth
import gdata.spreadsheets.client

import json
import re

OAUTH_SCOPES = [ "https://spreadsheets.google.com/feeds",
    "https://docs.google.com/feeds" ]
USER_AGENT = ""

BUDGET_HEADER = "Category"

@admin_required
def check_auth(request):
    return HttpResponse("SAPmonkey connected!")

@admin_required
def lookup_username(request, username):
    result = ESPUser.objects.filter(username=username)
    if len(result) == 0:
        result = ESPUser.objects.filter(username__iexact=username)
        if len(result) != 1:
            raise Http404()
    
    elif len(result) > 1:
        raise Http404()
    
    user = result[0]
    isMIT = user.email.strip().endswith("@mit.edu")
    
    response_data = {'isMIT': isMIT, 'name': user.name(), 'username': user.username}
    return HttpResponse(json.dumps(response_data), mimetype='application/json')

@admin_required
def list_budget_categories(request):
    srv = create_ss_service()
    worksheets = srv.get_worksheets(spreadsheet_key=settings.BUDGET_SPREADSHEET_KEY)
    
    response_data = dict()
    response_data['programs'] = list()
    response_data['categories'] = dict()
    
    # Insert extra budgets (e.x., for past programs, etc.)
    #  These go in Miscellaneous
    for c in settings.EXTRA_BUDGETS:
        response_data['programs'].append(c)
    
    # Iterate over each worksheet (i.e., each program's budget)
    for w in worksheets.entry:
        budget_categories = list()
        
        # Get contents of worksheet
        cell_feed = srv.get_cells(
            spreadsheet_key=settings.BUDGET_SPREADSHEET_KEY,
            worksheet_id=w.get_worksheet_id())
        
        # Find out how many rows are in the header (about 6)
        header_row = find_header_row(cell_feed, BUDGET_HEADER)
        if header_row is None:
            return HttpResponseServerError(
                'No header row found - looking for "' + BUDGET_HEADER +
                '" in column A of ' + w.title.text)
        
        # Iterate over the rows to list categories in the format
        #   "Big Category - Detailed Category" (i.e., "Publicity - Booth Candy")
        #
        # Direction: right-to-left, top-to-bottom
        # Note that items in Column 1 that contain '$' are subtotals, not
        #   categories, and are skipped
        category = "None"
        for cell_entry in cell_feed.entry:
            if int(cell_entry.cell.row) <= header_row:
                # Skip header rows
                continue
            
            if cell_entry.cell.col is '1':  # Col 1: "Big Category"
                if cell_entry.content.text is not None \
                    and cell_entry.content.text.find('$') == -1:
                    
                    category = cell_entry.content.text
            
            if cell_entry.cell.col is '2':  # Col 2: "Detailed Category"
                if cell_entry.content.text is not None:
                    item = category + ' - ' + cell_entry.content.text
                    budget_categories.append(item)
        
        response_data['programs'].append(w.title.text)
        response_data['categories'][w.title.text] = budget_categories
    
    return HttpResponse(json.dumps(response_data), mimetype='application/json')

@admin_required
def list_classes(request, program, select, username):
    pr = find_program(program)
    if not pr:
        raise Http404("Program not found")
    
    response_data = dict()
    response_data['program'] = program
    response_data['classes'] = list()
    
    if select == 'all':
        results = ClassSubject.objects.filter(parent_program=pr).order_by('id')
        for cs in results:
            response_data['classes'].append(format_class(cs))
    
    elif select == 'only':
        users = ESPUser.objects.filter(username=username)
        
        if len(users) != 1:
            raise Http404("Username not found")
            
        results = users[0].getTaughtClassesFromProgram(pr).order_by('id')
        for cs in results:
            response_data['classes'].append(format_class(cs))
    
    elif select == 'priority':
        users = ESPUser.objects.filter(username=username)
        
        if len(users) != 1:
            raise Http404("Username not found")
        
        results = users[0].getTaughtClassesFromProgram(pr).order_by('id')
        for cs in results:
            response_data['classes'].append(format_class(cs))
        
        full_results = ClassSubject.objects.filter(
            parent_program=pr).order_by('id')
        for cs in full_results:
            if cs not in results:
                response_data['classes'].append(format_class(cs))
    
    else:
        raise Http404("Unknown option")
    
    return HttpResponse(json.dumps(response_data), mimetype='application/json')

def create_ss_service():
    token = gdata.gauth.token_from_blob(settings.GOOGLE_CREDENTIALS)
    srv = gdata.spreadsheets.client.SpreadsheetsClient(source=USER_AGENT)
    srv = token.authorize(srv)
    return srv

def find_header_row(cell_feed, first_column_header):
    header_row = None
    for cell_entry in cell_feed.entry:
        if int(cell_entry.cell.col) != 1:
            continue
        
        if cell_entry.content.text == first_column_header:
            header_row = int(cell_entry.cell.row)
            break
    
    return header_row

def find_program(search):
    # Append the current year, if not included
    if not re.search('\d{4}', search):
        search += ' ' + str(settings.FISCAL_YEAR)
    
    # Given a string such as "Spring HSSP 2013", finds the corresponding program
    parts = search.split()
    
    # Find all programs where the parent type (e.g., "HSSP") and the friendly
    # name (e.g., "Spring 2013") both contain parts of the search text
    qParent = Q()
    qChild = Q()
    for p in parts:
        qParent = qParent | Q(anchor__parent__friendly_name__contains=p)
        qChild = qChild | Q(anchor__friendly_name__contains=p)
    
    # Find the first program that contains all parts of the search text
    results = Program.objects.filter(qParent, qChild)
    for r in results:
        names = r.niceName().split()
        i = 0
        for p in parts:
            for n in names:
                if p in n:
                    i += 1
                    break
        
        if i == len(parts):
            return r
    
    return None

def format_class(cs):
    name = ""
    
    symbol = cs.category.symbol
    if symbol:
        name += symbol
    
    name += str(cs.id)
    
    title = cs.title()
    if title:
        name += ': ' + title
    
    return name
