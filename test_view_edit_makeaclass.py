from django.test import TestCase
from django.urls import reverse

class EditMakeAClassViewTests(TestCase):
    def test_editclass_page_loads_with_expected_template(self):
        url = reverse('editclass')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])
        # If authenticated is required, 302 is okay
        self.assertTemplateUsed(response, "program/editclass.html")

    def test_makeaclass_page_loads_with_expected_template(self):
        url = reverse('makeaclass')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])
        self.assertTemplateUsed(response, "program/makeaclass.html")

    def test_makeaclass_form_contains_expected_fields(self):
        url = reverse('makeaclass')
        response = self.client.get(url)
        if response.status_code == 200:
            self.assertContains(response, "name=\"classname\"")
            self.assertContains(response, "name=\"subject\"")
