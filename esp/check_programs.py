#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')
sys.path.insert(0, '/app/esp')
django.setup()

from esp.program.models import Program

programs = Program.objects.all()
print(f"Total programs: {programs.count()}")
for p in programs[:10]:
    print(f"  - {p.url} ({p.name})")
