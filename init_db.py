
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')
django.setup()

from django.contrib.auth.models import User
from esp.program.models import Program
from esp.program.modules.models import ProgramModule, ProgramModuleObj

# 1. Create Superuser if not exists
if not User.objects.filter(username='supriyo').exists():
    User.objects.create_superuser('supriyo', 'supriyochowdhury760@gmail.com', 'password')
    print("Superuser 'supriyo' created.")

# 2. Create Program 'Splash/2026'
program, created = Program.objects.get_or_create(
    url='Splash/2026',
    defaults={
        'name': 'Splash 2026',
        'program_type': 'Splash',
        'program_instance': '2026'
    }
)
if created:
    print("Program 'Splash/2026' created.")

# 3. Associate Modules
# AdminCore (ID: 4 in previous session, let's look it up by name or assume ID)
# StudentRegCore (ID: 62)
admin_module = ProgramModule.objects.get(name='AdminCore')
student_reg_module = ProgramModule.objects.get(name='StudentRegCore')

ProgramModuleObj.objects.get_or_create(program=program, module=admin_module)
ProgramModuleObj.objects.get_or_create(program=program, module=student_reg_module)
print("Modules associated.")

# 4. Compile Theme
from esp.themes.controllers import ThemeController
ThemeController().load_theme('default')
print("Theme compiled.")
