from django.test import TestCase
from esp.program.modules.forms.rapidcheckin import RapidCheckinStudentWidget


class RapidCheckinStudentWidgetTests(TestCase):

    def test_widget_renders_text_and_hidden_inputs(self):
        widget = RapidCheckinStudentWidget()
        html = widget.render("student", None)

        self.assertIn('type="text"', html)
        self.assertIn('type="hidden"', html)
        self.assertIn('name="student_raw"', html)
        self.assertIn('name="student"', html)

    def test_widget_handles_invalid_value(self):
        widget = RapidCheckinStudentWidget()
        html = widget.render("student", "invalid")

        self.assertIn('type="text"', html)
        self.assertIn('type="hidden"', html)