from selenium.webdriver.support.ui import WebDriverWait
from sys import stderr, stdout, exc_info
import time

def noActiveAjax(driver):
    return driver.execute_script("return numAjaxConnections == 0")

def waitForAjax(driver):
    while(not noActiveAjax(driver)):
        time.sleep(1)

def try_login(driver, username, password):
    elem = driver.find_element_by_name("username")
    elem.send_keys(username)
    elem = driver.find_element_by_name("password")
    elem.send_keys(password)
    elem.submit()

def try_normal_login(driver, username, password):
    try_login(driver, username, password)
    driver.open_url("/")

def try_ajax_login(driver, username, password):
    try_login(driver, username, password)
    try:
        WebDriverWait(driver, 10).until(noActiveAjax)
    except:
        stderr.write(str(exc_info()[0]) + "\n")
        stderr.write("Wait for ajax login timed out.\n")
    driver.open_url("/")

def logout(driver):
    driver.open_url("/myesp/signout/")
    driver.open_url("/")
