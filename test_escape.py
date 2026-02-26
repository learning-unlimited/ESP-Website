import os
import sys

# setup django
sys.path.append(os.path.abspath('c:/Users/Dange/Downloads/ESP-Website-main/ESP-Website-fresh/esp'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")
import django
django.setup()

import json
from django.template import Template, Context

t = Template('<input type="hidden" name="{{ name }}" value="{{ value }}" />')
c = Context({'name': 'test_field', 'value': json.dumps([{"foo": "bar"}])})
print(t.render(c))
