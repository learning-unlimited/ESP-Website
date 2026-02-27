#!/usr/bin/env python
"""Patch teacherschedule.html to add Export column and calendar buttons."""

f = '/app/esp/templates/program/modules/programprintables/teacherschedule.html'
content = open(f).read()

# 1. Add Export header column
old_header = "    {% if moderators and teachers %}<th>Role</th> {% endif %}\n</tr>"
new_header = "    {% if moderators and teachers %}<th>Role</th> {% endif %}\n    <th>Export</th>\n</tr>"
content = content.replace(old_header, new_header)

# 2. Add Export buttons cell to each row
old_row = "    {% if moderators and teachers %}<td>{{ scheditem.role }}</td>{% endif %}\n</tr>"
new_row = (
    "    {% if moderators and teachers %}<td>{{ scheditem.role }}</td>{% endif %}\n"
    '  <td style="text-align: center;">\n'
    '      <a href="{{ scheditem.cls.google_calendar_url }}" target="_blank" title="Add to Google Calendar" style="text-decoration:none;font-size:0.9em;padding:2px 4px;background:#eee;border:1px solid #ccc;border-radius:4px;color:#333;margin-bottom:2px;display:inline-block;">[+ Google Calendar]</a><br/>\n'
    "      <a href=\"{% url 'studentschedule_ics' %}?secid={{ scheditem.cls.id }}\" title=\"Download .ics\" style=\"text-decoration:none;font-size:0.9em;padding:2px 4px;background:#eee;border:1px solid #ccc;border-radius:4px;color:#333;display:inline-block;\">&#128197; Apple/Outlook</a>\n"
    '  </td>\n'
    '</tr>'
)
content = content.replace(old_row, new_row)

open(f, 'w').write(content)
print('SUCCESS - Export column and buttons added')
