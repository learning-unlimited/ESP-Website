from __future__ import absolute_import
import json
import re
from unittest import mock

import six

from reversion import revisions as reversion

from esp.program.models import NametagBack, Program
from esp.program.modules.handlers import nametagmodule
from esp.program.modules.handlers.nametagmodule import _back_preview, check_nametag_back
from esp.program.tests import ProgramFrameworkTest
from esp.utils.latex import texsafe
from esp.tests.util import CacheFlushTestCase as TestCase


class TexSafeTest(TestCase):
    def test_keeps_supported_letters(self):
        self.assertEqual(texsafe(u'Jos\u00e9 W\u00f3jcik'), (u'Jos\u00e9 W\u00f3jcik', False))

    def test_escapes_specials(self):
        self.assertEqual(texsafe(u'a&b_c%{d}\\')[0], u'a\\&b\\_c\\%\\{d\\}\\textbackslash{}')

    def test_curly_apostrophe_is_not_a_loss(self):
        self.assertEqual(texsafe(u'O\u2019Brien'), (u"O'Brien", False))

    def test_falls_back_to_base_letter(self):
        self.assertEqual(texsafe(u'Nguy\u1ec5n'), (u'Nguyen', True))

    def test_replaces_other_scripts(self):
        self.assertEqual(texsafe(u'\u738b\u5c0f'), (u'??', True))


class NameTagModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 2, 'num_teachers': 2, 'num_admins': 1})
        super(NameTagModuleTest, self).setUp(*args, **kwargs)
        self.admin = self.admins[0]
        self.admin.set_password('password')
        self.admin.save()
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.base = '/manage/%s/' % self.program.getUrlBase()

    def other_program_back(self, name='Back', source='Elsewhere'):
        other = Program.objects.create(url='Other/1999', name='Other 1999', grade_min=7, grade_max=12)
        back = NametagBack.objects.create(name=name, program=other, source=source)
        return back

    def generate(self, suffix='', **data):
        post = {'type': 'misc', 'progname': 'Splash 2026', 'misc_info': 'Ann Lee, Admin'}
        post.update(data)
        return self.client.post(self.base + 'generatetags' + suffix, post)

    def make_back(self, source=r'\textbf{Hello \& welcome}'):
        back = NametagBack.objects.create(name='Back', program=self.program, source=source)
        return back

    def save(self, **data):
        post = {'name': 'Back', 'source': 'Hello'}
        post.update(data)
        response = self.client.post(self.base + 'nametagbacksave', post)
        return json.loads(response.content.decode('utf8'))

    def test_blank_back_has_no_back_pages(self):
        tex = self.generate('/tex').content.decode('utf8')
        self.assertEqual(tex.count(r'\end{picture}'), 2)
        self.assertNotIn('Back for', tex)

    def test_back_pages_interleave_and_mirror(self):
        back = self.make_back()
        tex = self.generate('/tex', nametag_back=back.id, misc_info='Ann Lee, Admin\nBo Li, Admin').content.decode('utf8')
        pages = tex.split(r'\end{picture}')[:-1]
        self.assertEqual(len(pages), 4)
        self.assertNotIn(r'\put', pages[1])
        self.assertIn('Ann Lee', pages[2])
        self.assertIn(r'\usebox{\backbox}', pages[3])
        self.assertIn(r'Hello \& welcome', tex)
        self.assertNotIn('&amp;', tex)
        # Slot 0 of the front is in the left column; its back is in the right.
        first_front = re.search(r'\\put\(([\d.]+),[\d.]+\)\{\\makebox\(0,0\)\[lt\]\{\\ntfront', pages[2]).group(1)
        first_back = re.search(r'\\put\(([\d.]+),[\d.]+\)\{\\makebox\(0,0\)\[lt\]\{\\usebox', pages[3]).group(1)
        self.assertEqual(first_front, '0.450')
        self.assertEqual(first_back, '4.400')

    def test_offsets_move_only_backs(self):
        back = self.make_back()
        tex = self.generate('/tex', nametag_back=back.id, back_x_offset='0.25', back_y_offset='0.5').content.decode('utf8')
        pages = tex.split(r'\end{picture}')[:-1]
        self.assertIn(r'\put(0.450,9.900){\makebox(0,0)[lt]{\ntfront', pages[2])
        self.assertIn(r'\put(4.650,9.350){\makebox(0,0)[lt]{\usebox', pages[3])

    def test_rejects_bad_offsets(self):
        for value in ('nan', 'inf', '5', 'abc'):
            response = self.generate('/tex', back_x_offset=value)
            self.assertNotIn('documentclass', response.content.decode('utf8'))

    def test_back_and_barcodes_are_exclusive(self):
        response = self.generate('/tex', nametag_back=self.make_back().id, barcodes='on')
        self.assertIn('Please choose one', response.content.decode('utf8'))

    def test_pdf_survives_hostile_names(self):
        names = u'\n'.join([
            u'\u738b\u5c0f\u660e, Student', u'\u0645\u062d\u0645\u062f, Student', u'Sam \U0001F642, Student',
            u'Nguy\u1ec5n, Student', u'\\end{document} & 100% #_$^~{, Student', u'\u0126\u017f, Student',
            u'A' * 300 + u', Student', u'Ann, Admin, he/him \\input{x}',
        ])
        response = self.generate(misc_info=names, nametag_back=self.make_back().id)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_flags_unprintable_names_on_test_sheet(self):
        tex = self.generate('/tex', misc_info=u'\u738b\u5c0f\u660e, Student').content.decode('utf8')
        self.assertIn('could not be printed', tex.split(r'\end{picture}')[0])

    def test_every_supported_letter_compiles(self):
        letters = u''.join(six.unichr(c) for c in range(0xC0, 0x180) if texsafe(six.unichr(c)) == (six.unichr(c), False))
        self.assertGreater(len(letters), 150)
        lines = u'\n'.join(u'%s, Student' % letters[i:i + 20] for i in range(0, len(letters), 20))
        self.assertTrue(self.generate(misc_info=lines).content.startswith(b'%PDF'))

    def test_barcode_pdf(self):
        response = self.generate(type='teacher', barcodes='on')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_mistakes_are_reported(self):
        cases = [(r'\textbf{oops', None), (r'\nosuchmacro', 'Line 1'), ('Food & drink', 'Line 1'),
                 ('ok\n\n' + r'\nosuchmacro', 'Line 3'), (r'\includegraphics{nosuch.png}', 'nosuch.png'),
                 (r'a \end{document} b', None), (u'Room \u738b', None)]
        for source, expected in cases:
            error = check_nametag_back(source)['error']
            self.assertTrue(error, source)
            if expected:
                self.assertIn(expected, error)

    def test_trailing_percent_is_harmless(self):
        self.assertIsNone(check_nametag_back('50% off')['error'])

    def test_infinite_loop_times_out(self):
        with mock.patch.object(nametagmodule, 'BACK_COMPILE_TIMEOUT', 1):
            self.assertIn('too long', check_nametag_back(r'\def\a{\a}\a')['error'])

    def test_margin_warnings(self):
        self.assertIsNone(_back_preview('short')['warning'])
        self.assertIn('bottom', _back_preview(r'line\par ' * 40)['warning'])
        self.assertIn('right', _back_preview(r'\rule{6in}{1pt}')['warning'])
        self.assertIn('left', _back_preview(r'\hspace*{-0.09in}\rule{1in}{1in}')['warning'])
        self.assertIsNone(_back_preview(r'\hspace*{-0.03in}\rule{1in}{1in}')['warning'])
    def test_margin_problem_warns_but_saves(self):
        result = self.save(source=r'\rule{6in}{1pt}')
        self.assertTrue(result['image'])
        self.assertIsNone(result['error'])
        self.assertIn('WARNING', result['warning'])
        self.assertTrue(NametagBack.objects.filter(program=self.program).exists())
    def test_tight_margins_can_print_but_broken_latex_cannot(self):
        response = self.generate('/tex', nametag_back=self.make_back(r'\rule{6in}{1pt}').id)
        self.assertIn('documentclass', response.content.decode('utf8'))
        NametagBack.objects.filter(program=self.program).delete()
        response = self.generate('/tex', nametag_back=self.make_back(r'\nosuchmacro').id)
        self.assertIn('needs fixing', response.content.decode('utf8'))
    def test_save_returns_image_or_error(self):
        result = self.save(source=r'\textbf{Hi}')
        self.assertTrue(result['image'].startswith('data:image/png;base64,'))
        result = self.save(name='Other', source=r'\nosuchmacro')
        self.assertIsNone(result['image'])
        self.assertIn('Undefined control sequence', result['error'])
    def test_save_creates_version_history(self):
        self.save()
        back = NametagBack.objects.get(program=self.program, name='Back')
        self.save(back_id=back.id, source='Second')
        back.refresh_from_db()
        self.assertEqual(back.source, 'Second')
        versions = list(reversion.get_for_object(back))
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].revision.user_id, self.admin.id)
        self.assertEqual(versions[0].revision.comment, 'Edited')
        self.assertEqual(versions[1].revision.comment, 'Created')
        self.assertEqual(versions[1].field_dict['source'], 'Hello')

    def test_invalid_latex_is_not_saved(self):
        result = self.save(source=r'\nosuchmacro')
        self.assertFalse(NametagBack.objects.filter(program=self.program).exists())
        self.assertIn('Undefined control sequence', result['error'])

    def test_importing_copies_into_this_program(self):
        other = self.other_program_back()
        self.save(back_id=other.id, name='Back', source='Custom')
        self.assertEqual(other.source, 'Elsewhere')
        other.refresh_from_db()
        self.assertEqual(NametagBack.objects.get(program=self.program, name='Back').source, 'Custom')
    def test_name_clash_does_not_overwrite(self):
        existing = self.make_back(source='Original')
        result = self.save(name='Back', source='Replace')
        self.assertIn('already has a back', result['error'])
        existing.refresh_from_db()
        self.assertEqual(existing.source, 'Original')
    def test_save_returns_refreshed_options(self):
        result = self.save(name='Fresh')
        back = NametagBack.objects.get(program=self.program, name='Fresh')
        self.assertEqual(result['id'], back.id)
        self.assertIn('value="%d"' % back.id, result['options_html'])

    def load(self, back):
        return json.loads(self.client.get(self.base + 'nametagbackload', {'back': back.id}).content.decode('utf8'))

    def test_load_previews_all_backs_and_flags_imports(self):
        own = self.load(self.make_back())
        self.assertFalse(own['importing'])
        self.assertTrue(own['image'])
        imported = self.load(self.other_program_back())
        self.assertTrue(imported['importing'])
        self.assertEqual(imported['source'], 'Elsewhere')
        self.assertTrue(imported['image'])

    def import_back(self, back, name='Back'):
        response = self.client.post(self.base + 'nametagbackimport', {'back_id': back.id, 'name': name})
        return json.loads(response.content.decode('utf8'))

    def test_import_copies_server_side(self):
        other = self.other_program_back()
        result = self.import_back(other)
        copy = NametagBack.objects.get(program=self.program, name='Back')
        self.assertEqual(result['id'], copy.id)
        self.assertEqual(copy.source, 'Elsewhere')
        other.refresh_from_db()
        self.assertEqual(other.source, 'Elsewhere')
        self.assertTrue(result['image'])
        self.assertEqual(reversion.get_for_object(copy)[0].revision.comment, 'Imported from Other 1999: Back')

    def test_broken_back_can_still_be_imported_to_fix_it(self):
        result = self.import_back(self.other_program_back(source=r'\nosuchmacro'))
        self.assertIn('Undefined control sequence', result['error'])
        self.assertEqual(result['id'], NametagBack.objects.get(program=self.program, name='Back').id)

    def test_import_name_clash_keeps_existing(self):
        existing = self.make_back(source='Mine')
        result = self.import_back(self.other_program_back())
        self.assertIn('already has a back', result['error'])
        self.assertNotIn('id', result)
        existing.refresh_from_db()
        self.assertEqual(existing.source, 'Mine')

    def test_cannot_import_own_back_or_require_non_admin(self):
        self.assertIn('no longer', self.import_back(self.make_back())['error'])
        other = self.other_program_back()
        self.client.logout()
        self.client.post(self.base + 'nametagbackimport', {'back_id': other.id, 'name': 'Nope'})
        self.assertFalse(NametagBack.objects.filter(name='Nope').exists())
    def test_cannot_print_another_programs_back(self):
        response = self.generate('/tex', nametag_back=self.other_program_back().id)
        self.assertNotIn('documentclass', response.content.decode('utf8'))
        response = self.generate('/tex', nametag_back='new')
        self.assertNotIn('documentclass', response.content.decode('utf8'))
    def test_load_and_save_require_admin(self):
        self.client.logout()
        self.assertNotIn('source', self.client.get(self.base + 'nametagbackload', {'back': 1}).content.decode('utf8'))
        self.client.post(self.base + 'nametagbacksave', {'name': 'Nope', 'source': 'x'})
        self.assertFalse(NametagBack.objects.filter(name='Nope').exists())
    def test_print_page_has_editor_and_calibration(self):
        content = self.client.get(self.base + 'selectidoptions').content.decode('utf8')
        self.assertIn('id="back-source"', content)
        self.assertIn('id="back-preview-card"', content)
        self.assertIn('value="calibration"', content)
    def test_dropdown_order_and_create_new(self):
        current = self.make_back()
        newer_program = Program.objects.create(url='Newer/2099', name='Newer 2099', grade_min=7, grade_max=12)
        newer = NametagBack.objects.create(name='Back', program=newer_program, source='x')
        content = self.client.get(self.base + 'selectidoptions').content.decode('utf8')
        select = content[content.index('name="nametag_back"'):]
        select = select[:select.index('</select>')]
        self.assertEqual(select.count('value="new"'), 1)
        self.assertIn('Create from scratch', select)
        self.assertIn('label="Import from Newer 2099"', select)
        self.assertIn('label="%s"' % self.program.niceName(), select)
        self.assertIn('>Back</option>', select)
        self.assertNotIn(': Back', select)
        positions = [select.index('Blank'), select.index('value="%d"' % newer.id),
                     select.index('value="new"'), select.index('value="%d"' % current.id)]
        self.assertEqual(positions, sorted(positions))
    def check_single_grid(self, page):
        verticals = re.findall(r'\\put\(([\d.]+),[\d.]+\)\{\\line\(0,1\)\{9\.000\}\}', page)
        self.assertEqual(sorted(verticals), ['0.350', '4.250', '8.150'])
        self.assertEqual(len(re.findall(r'\{\\line\(1,0\)\{7\.800\}\}', page)), 4)
        self.assertNotIn(r'\fbox', page)

    def test_normal_first_sheet_is_plain_with_blank_back(self):
        tex = self.generate('/tex', nametag_back=self.make_back().id).content.decode('utf8')
        pages = tex.split(r'\end{picture}')
        self.check_single_grid(pages[0])
        self.assertNotIn(r'\line(0,1){0.850}', pages[0])
        self.assertNotIn(r'\line(1,0){0.500}', pages[0])
        self.assertNotIn(r'\put', pages[1])
        self.assertIn(r'\line(0,1){0.850}', pages[2])

    def calibration(self, **data):
        return self.generate('/tex', type='calibration', **data).content.decode('utf8').split(r'\end{picture}')[:-1]

    def test_calibration_is_one_sheet_with_short_marks(self):
        pages = self.calibration()
        self.assertEqual(len(pages), 2)
        self.check_single_grid(pages[0])
        self.check_single_grid(pages[1])
        self.assertEqual(len(re.findall(r'\\line\(0,1\)\{0\.200\}', pages[0])), 4)
        self.assertEqual(len(re.findall(r'\\line\(1,0\)\{0\.500\}', pages[0])), 2)
        self.assertIn(r'\ntcenterlabel{\#1}', pages[0])
        self.assertIn(r'\ntcenterlabel{\#2 back}', pages[1])
        self.assertNotIn('Back for', pages[1])
    def test_calibration_back_has_four_scales_inside_the_grid(self):
        back_sheet = self.calibration()[1]
        self.assertEqual(len(re.findall(r'\\line\(0,-?1\)\{0\.(?:16|08)0\}', back_sheet)), 2 * 41)
        self.assertEqual(len(re.findall(r'\\line\(-?1,0\)\{0\.(?:16|08)0\}', back_sheet)), 2 * 41)
        self.assertEqual(len(re.findall(r'\\line\(-?[01],-?[01]\)\{0\.160\}', back_sheet)), 4 * 11)
        self.assertIn(r'\put(4.250,9.900){\line(0,-1){0.160}}', back_sheet)
        self.assertIn(r'\put(4.250,1.100){\line(0,1){0.160}}', back_sheet)
    def test_scales_move_with_offsets(self):
        back_sheet = self.calibration(back_x_offset='0.25', back_y_offset='0.1')[1]
        self.assertIn(r'\put(4.500,9.800){\line(0,-1){0.160}}', back_sheet)
        self.assertIn(r'\put(0.600,5.400){\line(1,0){0.160}}', back_sheet)
