from django.http import HttpResponse
from factory import Factory
import simplejson as json

class ResponseFactory(Factory):
    FACTORY_FOR = HttpResponse

    content = None
    status = 200

class JsonResponseFactory(ResponseFactory):
    content_type = 'application/json'

class ErrorLoginResponseFactory(JsonResponseFactory):
    content = json.dumps({
        'message': 'Invalid username or password'
    })

class StudentLoginResponseFactory(JsonResponseFactory):
    content = json.dumps({
        'success': 'true',
        'isStudent': 'true',
        'isOnsite': 'false'
    })

class OnsiteLoginResponseFactory(JsonResponseFactory):
    content = json.dumps({
        'success': 'true',
        'isStudent': 'false',
        'isOnsite': 'true'
    })

class ProgramResponseFactory(JsonResponseFactory):
    content = json.dumps([
        {
            'id': 1,
            'title': 'Test Program 1',
            'baseUrl': 'test/Program1'
        },
        {
            'id': 2,
            'title': 'Test Program 2',
            'baseUrl': 'test/Program2'
        }
    ])
