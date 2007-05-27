from django.test import TestCase
from users.models import ESPUser, UserBit
from django.test.client import Client
from esp.tests.util import build_posts
from django.contrib.auth.models import User


class ESPUserTestCase(TestCase):
    fixtures = ['users']

    def setUp(self):
        from esp.datatree.models import GetNode
        from esp.program.models  import Program
        node = GetNode('Q/Programs/Dummy_Programs/Profile_Storage')
        dummy_program = Program(anchor = node,
                                grade_min = 13,
                                grade_max = 13,
                                director_email = 'esp-webmasters@mit.edu',
                                class_size_min = 9999,
                                class_size_max = 9999)

        dummy_program.save()
                                
        
        self.client = Client()


    def test_dtails(self):


        print "Testing User Reg Form\n===============================\n"
        test_user_params = dict()
        test_user_joins  = dict()       

        # First we are going to test the user account creation form.
        # We create a list of test data in the following format:
        # tuple of tuples: the second term in each tuple says whether or
        # not the creation should fail (by failure, status code is still 200).
        test_user_params['first_name'] = (
            # Disabled for now:
            #(None, False), # null
            ('', False), # blank
            ('   ', False), # blank
            ('52av3fasdf', True),
            ('a', True),
            ('%'*12, True),
            ('A'*128, False), # too long
        )

        test_user_params['last_name'] = (
            # Disabled for now:
            #(None, False), # null
            #('teatasdfXX__#$#$AAasdfsdsf', False), # still works
            (' ', False), # blank
            ('a', True),
            ('%^'*12, True),
            ('A'*128, False), # Too Long
        )

        test_user_params['username'] = (
            # Disabled for now
            #(None, False), # null
            #('%%!$&', False), # invalid characters
            ('', False), # blank
            ('abcd', True),
            ('a'*33, False), # too long
        )

        # user roles
        test_user_params['role'] = (
            ('Student', True),
            ('Teacher', True),
            ('Guardian', True),
            ('Educator', True),
            ('educator', False), # not one of the list
            ('', False), # blank
            (None, False), # null
        )

        test_user_params['email'] = (
            # Disabled for now
            #('a'*15+'@mit.edu', False), # longer than 15 characters           
            ('abcd@jj.com', True),
            ('mike@axiak.net', True),
            ('foo@mit.edu', True),
            ('', False),
            ('asdfasdfasdfasdf', False),
        )


        # test_user_joins specify join'd tests
        # this allows one to test field's validity against each other.
        test_user_joins['password'] = (
            # Disabled for now
            # one none
            # ({'password': None,
            # 'password_confirm': ''},
            # False),
             # other none
#            ({'password': 'a',
#              'password_confirm': None},
#             False),
             # both none
#             ({'password': None,
#               'password_confirm': None},
#              False),

            ({'password': 'abcdef',
              'password_confirm': 'abcdef'},
             True),
            ({'password': 'abcdef',
              'password_confirm': 'abcde'},
             False),
            ({'password': '',
              'password_confirm': ''},
             False),
            ({'password': 'a',
              'password_confirm': ''},
             False),
             # case sensitivity
            ({'password': 'A',
              'password_confirm': 'a'},
             False),
        )              


        posts = build_posts(test_user_params, test_user_joins)
        i = 1
        for post_kwargs, success_expected in posts:
            response = self.client.post('/myesp/finish/', post_kwargs)
            self.failUnlessEqual(response.status_code, 200)
            #print type(response)
            if (len(response.context[0]['form'].error_dict) == 0) and success_expected != True:
                assert False, "User Reg Form: Test %s FAILED\nPost:\n%s\n\nForm Errors: %s\n\nExpected Form Problems: %s" \
                       % (i, post_kwargs, response.context[0]['form'].error_dict, '\n'.join(success_expected))

            
            if success_expected != True:
                print "User Reg Form: Test %s succeeded (form %s)" % (i, (success_expected == True) and 'succeeded' or 'failed')
                i+=1
                continue

            username = post_kwargs['username']
            password = post_kwargs['password']

            user_response = self.client.post('/myesp/login/', {'username':username,'password':password,'op':'login'})
            if not user_response or not user_response.status_code == 302:
                print '\n'.join([str(user.__dict__) for user in User.objects.all()])
                assert False, "User Reg Form: Test %s FAILED\nUser %s did not login!\nPost:\n%s\n\nForm Errors: %s\n\nExpected Form Problems: %s" \
                       % (i, username, post_kwargs,
                          response.context[0]['form'].error_dict,success_expected)

            userobj = User.objects.get(username = username)
            userobj.delete()
            del userobj
            
            print "User Reg Form: Test %s succeeded (form %s)" % (i, (success_expected == True) and 'succeeded' or 'failed')
            i += 1
            
        print "User Reg Form Test Completed\n===============================\n\n"

        test_user_list = []

        for role in ['Student','Teacher','Educator','Guardian']:
            test_user_list.append({'username'        : 'test' + role,
                                   'password'        : 'abcdef',
                                   'password_confirm': 'abcdef',
                                   'first_name'      : 'testx',
                                   'last_name'       :  'testy',
                                   'role'            :  role,
                                   'email'           :  'esp-webmasters@mit.edu'})

        for post_kwargs in test_user_list:
            response = self.client.post('/myesp/finish/', post_kwargs)



        test_user_params = dict()
        test_user_joins  = dict()       

        # First we are going to test the user account creation form.
        # We create a list of test data in the following format:
        # tuple of tuples: the second term in each tuple says whether or
        # not the creation should fail (by failure, status code is still 200).
        test_user_params['first_name'] = (
            # Disabled for now:
            #(None, False), # null
            ('', False), # blank
            ('   ', False), # blank
            ('52av3fasdf', True),
            ('a', True),
            ('%'*12, True),
            ('A'*128, False), # too long
        )
        
            
            
            
        response = self.client.get('/test')


        
