def noActiveAjaxJQuery(selenium):
    return selenium.execute_script("return $j.active == 0")

def try_login(selenium, username, password):
    username_input = selenium.find_element_by_name("username")
    username_input.send_keys(username)
    password_input = selenium.find_element_by_name("password")
    password_input.send_keys(password)
    selenium.find_element_by_id('gologin').click()

def try_normal_login(selenium, live_server_url, username, password):
    try_login(selenium, username, password)
    selenium.get('%s%s' % (live_server_url, "/"))

def logout(selenium, live_server_url):
    selenium.get('%s%s' % (live_server_url, "/myesp/signout/"))
    selenium.get('%s%s' % (live_server_url, "/"))
