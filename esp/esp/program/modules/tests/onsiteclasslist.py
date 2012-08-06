from esp.program.tests import ProgramFrameworkTest

import simplejson as json

class OnsiteClassListTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(OnsiteClassListTest, self).setUp()
        self.add_student_profiles()
        self.client.login(username=self.onsites[0].username, password="password")

    def testStudentListJson(self):
        resp = self.client.get("/onsite/%s/get_student_list_json" % self.program.getUrlBase())
        self.assertTrue(resp.status_code == 200)

        students = sorted(json.loads(resp.content), key=lambda student: student['id'])
        self.assertEqual(len(students), len(self.students))

        for student1, student2 in zip(students, self.students):
            self.assertEqual(student1['username'], student2.username)
            self.assertEqual(student1['first_name'], student2.first_name)
            self.assertEqual(student1['last_name'], student2.last_name)
            self.assertEqual(student1['id'], student2.id)
            self.assertEqual(student1['email'], student2.email)

    def testStudentJson(self):
        # fill in more details for profile
        student1 = self.students[1]
        student1.first_name = 'Master'
        student1.last_name = 'Yoda'
        student1.save()

        profile = student1.getLastProfile()
        edu = profile.student_info
        edu.school = 'Jedi Temple'
        edu.graduation_year = 911
        edu.save()

        from esp.users.models import ContactInfo
        contact = ContactInfo(address_street='1 Swamp Street',
                              address_city='Sluis Sector',
                              address_state='CA',
                              address_zip='00000',
                              e_mail='yoda@jedi.org',
                              phone_cell='1234567890')
        contact.save()

        profile.contact_user = contact
        profile.save()

        resp = self.client.get("/onsite/%s/get_student_json?id=%d" % (self.program.getUrlBase(), student1.id))
        self.assertTrue(resp.status_code == 200)

        student2 = json.loads(resp.content)

        user_info = student2['user']
        self.assertEqual(user_info['id'], student1.id)
        self.assertEqual(user_info['name'], '%s %s' % (student1.first_name, student1.last_name))
        self.assertEqual(user_info['grade'], student1.getGrade())

        from esp.users.models import UserBit
        from esp.datatree.models import GetNode
        checkin_status = 'true' if UserBit.valid_objects().filter(user=student1, qsc=self.program.anchor, verb=GetNode('V/Flags/Registration/Attended')) else 'false'
        self.assertEqual(user_info['checkin_status'], checkin_status)

        student_info = student2['student']
        self.assertEqual(student_info['school'], edu.school)
        self.assertEqual(student_info['graduation_year'], edu.graduation_year)
        self.assertEqual(student_info['dob'], '' if edu.dob is None else edu.dob.isoformat())

        address = '%s,\n%s, %s %s' % (contact.address_street, contact.address_city, contact.address_state, contact.address_zip)
        contact_info = student2['contact']
        self.assertEqual(contact_info['address'], address)
        self.assertEqual(contact_info['email'], contact.e_mail)
        self.assertEqual(contact_info['phone_day'], contact.phone_day)
        self.assertEqual(contact_info['phone_cell'], contact.phone_cell)

    def testStudentEnrollmentJson(self):
        self.schedule_randomly()
        self.classreg_students()

        student = self.students[2]
        resp = self.client.get("/onsite/%s/get_student_enrollment_json?id=%d" % (self.program.getUrlBase(), student.id))
        self.assertTrue(resp.status_code == 200)

        schedule1 = sorted(self.student_schedules[int(student.id)])
        schedule2 = sorted(json.loads(resp.content)['sections'], key=lambda section: section['section__id'])
        for first, second in zip(schedule1, schedule2):
            self.assertEqual(first, second['section__id'])
