"""Re-export all views for backward compatibility with existing URL configs."""
from esp.program.views.user_management import usersearch, userview, userview_edit, deactivate_user, activate_user, unenroll_student
from esp.program.views.program_management import manage_programs, newprogram
from esp.program.views.payment import submit_transaction
from esp.program.views.page_management import manage_pages
from esp.program.views.cache_management import flushcache
from esp.program.views.email_management import emails
from esp.program.views.settings_management import tags, redirects, catsflagsrecs
from esp.program.views.statistics_views import statistics
from esp.program.views.documentation import manage_docs
