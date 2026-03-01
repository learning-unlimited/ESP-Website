#!/usr/bin/env python
"""Patch teacherschedule.html to fix the url tag."""

f = '/app/esp/templates/program/modules/programprintables/teacherschedule.html'
content = open(f).read()

# Replace the {% url 'studentschedule_ics' %}?secid=... with a direct relative URL
old = "{% url 'studentschedule_ics' %}?secid={{ scheditem.cls.id }}"
new = "/learn/{{ program.url }}/studentschedule_ics?secid={{ scheditem.cls.id }}"
content = content.replace(old, new)

open(f, 'w').write(content)
print('DONE - replaced url tag with direct path')
