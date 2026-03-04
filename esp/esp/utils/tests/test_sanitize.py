from django.test import SimpleTestCase
from esp.utils.sanitize import strip_base64_images


class StripBase64ImagesTest(SimpleTestCase):

    def test_none_input(self):
        result, count = strip_base64_images(None)
        self.assertIsNone(result)
        self.assertEqual(count, 0)

    def test_empty_string(self):
        result, count = strip_base64_images("")
        self.assertEqual(result, "")
        self.assertEqual(count, 0)

    def test_no_data_uri(self):
        html = '<p>Hello world</p>'
        result, count = strip_base64_images(html)
        self.assertEqual(result, html)
        self.assertEqual(count, 0)

    def test_strip_img_tag(self):
        html = '<p>Text</p><img src="data:image/png;base64,AAA" /><p>More</p>'
        result, count = strip_base64_images(html)
        self.assertEqual(result, '<p>Text</p><p>More</p>')
        self.assertEqual(count, 1)

    def test_strip_css_data_uri(self):
        html = '<div style="background-image: url(data:image/png;base64,AAA)"></div>'
        result, count = strip_base64_images(html)
        self.assertIn('url()', result)
        self.assertEqual(count, 1)

    def test_strip_multiple_occurrences(self):
        html = '''
        <img src="data:image/png;base64,AAA">
        <div style="background:url(data:image/png;base64,BBB)"></div>
        '''
        result, count = strip_base64_images(html)
        self.assertNotIn('data:image', result)
        self.assertEqual(count, 2)

    def test_broken_img_tag(self):
        html = '<img src="data:image/png;base64,AAA"'
        result, count = strip_base64_images(html)
        # Should not crash
        self.assertEqual(result, html)
        self.assertEqual(count, 0)