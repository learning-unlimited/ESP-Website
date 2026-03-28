from django.test import Client
from django.db import connection
from django.test.utils import CaptureQueriesContext

from esp.program.tests import ProgramFrameworkTest
from esp.application.models import StudentProgramApp, StudentClassApp

class AdmissionsDashboardTest(ProgramFrameworkTest):
    """ Regression test for N+1 query in AdmissionsDashboard.apps() """

    DEFAULT_SETTINGS = {
        'num_students': 5,
        'num_teachers': 1,
        'num_admins': 1,
        'num_categories': 1,
        'num_rooms': 1,
        'classes_per_teacher': 1,
        'sections_per_class': 1,
    }

    def setUp(self):
        super(AdmissionsDashboardTest, self).setUp(**self.DEFAULT_SETTINGS)
        self.client = Client()
        self.admin = self.admins[0]
        self.cls = self.program.classes()[0]

    def _create_app(self, student):
        app = StudentProgramApp.objects.create(
            user=student,
            program=self.program,
            admin_status=StudentProgramApp.APPROVED,
            app_type='Formstack'
        )
        StudentClassApp.objects.create(
            app=app,
            subject=self.cls,
            student_preference=1,
            admission_status=StudentClassApp.ADMITTED
        )

    def test_apps_query_count_flat(self):
        self.client.login(username=self.admin.username, password='password')
        url = self.program.get_manage_url() + 'admissionsdashboard/apps'
        
        # Add 1 application, measure queries
        self._create_app(self.students[0])
        
        with CaptureQueriesContext(connection) as ctx1:
            response1 = self.client.get(url)
        
        self.assertEqual(response1.status_code, 200)
        queries1 = len(ctx1.captured_queries)
        
        # Add 4 more applications, making it 5 total
        for student in self.students[1:]:
            self._create_app(student)
            
        with CaptureQueriesContext(connection) as ctx2:
            response2 = self.client.get(url)
            
        self.assertEqual(response2.status_code, 200)
        queries2 = len(ctx2.captured_queries)
        
        self.assertEqual(
            queries1, queries2, 
            "Query count increased from %d to %d when applications increased "
            "from 1 to 5. N+1 query issue exists." % (queries1, queries2)
        )
