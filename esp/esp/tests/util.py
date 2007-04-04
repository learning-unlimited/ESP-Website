import pickle
from esp.web.util.structures import cross_set


def build_posts(test_user_params = {}, test_user_joins = {}):
    """ This function will create a list of dictionaries to post to
        a web site. Useful for testing. An example using this lives in
        esp.user.tests.
    """
    
    build_posts = list()
    post_sets   = dict()

    for form, values in test_user_params.iteritems():
        tmp_list = []
        for value in values:
            tmp_list.append((form, value))
        post_sets[form] = tmp_list

    for form, values in test_user_joins.iteritems():
        tmp_list = []
        for value in values:
            tmp_list.append((form, pickle.dumps(value)))
        post_sets[form] = tmp_list

    new_post = reduce(lambda x,y:x*y,
                      [cross_set(value) for value in post_sets.values()])

    for post in new_post:
        tmp_dict = dict()
        expect_success = []

        for form, value in post:
            if type(value) == str:
                new_value = pickle.loads(value)
                if new_value[1] == False:
                    expect_success.append(form)
                tmp_dict.update(new_value[0])

            else:
                if value[1] == False:
                    expect_success.append(form)
                tmp_dict[form] = value[0]
                
        if expect_success == []:
            expect_success = True
        build_posts.append((tmp_dict, expect_success))

    return build_posts
