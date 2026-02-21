from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType
from esp.tagdict.models import Tag
import random

class FormstackMedliabTest(ProgramFrameworkTest):
    def setUp(self):
        super(FormstackMedliabTest, self).setUp()
        # Set up Formstack tags for the program so the template renders correctly
        Tag.setProgramTag("formstack_id", "12345", self.program)
        Tag.setProgramTag("formstack_viewkey", "abcde", self.program)

    def test_completion_indicator(self):
        """Test that the completion indicator appears only when the user has completed the form."""
        # Pick a student and log in
        student = random.choice(self.students)
        self.assertTrue(self.client.login(username=student.username, password='password'), 
                        "Couldn't log in as student %s" % student.username)

        # 1. Check BEFORE completion
        url = '/learn/%s/medliab' % self.program.url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'You have already completed this medical form')

        # 2. Complete the form (create a Record)
        rt = RecordType.objects.get(name="med")
        Record.objects.create(user=student, event=rt, program=self.program)

        # 3. Check AFTER completion
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have already completed this medical form')
