from __future__ import absolute_import
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def noActiveAjaxJQuery(selenium):
    return selenium.execute_script("return $j.active == 0")


def try_login(selenium, username, password):
    username_input = WebDriverWait(selenium, 10).until(
        EC.visibility_of_element_located((By.NAME, "username"))
    )
    username_input.send_keys(username)
    password_input = selenium.find_element(By.NAME, "password")
    password_input.send_keys(password)
    selenium.find_element(By.ID, 'gologin').click()


def try_normal_login(selenium, live_server_url, username, password):
    try_login(selenium, username, password)

    def login_completed(driver):
        cookie = driver.get_cookie('cur_username')
        return cookie and cookie.get('value') == username

    WebDriverWait(selenium, 10).until(login_completed)
    selenium.get('%s%s' % (live_server_url, "/"))


def logout(selenium, live_server_url):
    selenium.get('%s%s' % (live_server_url, "/myesp/signout/"))
    selenium.get('%s%s' % (live_server_url, "/"))
