from django.core.urlresolvers import reverse
from django_selenium.testcases import SeleniumTestCase
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from esp.utils.models import TemplateOverride
from esp.users.models import ESPUser

from sys import stderr, stdout, exc_info

import time

def noActiveAjax(driver):
    return driver.execute_script("return numAjaxConnections == 0")

def waitForAjax(driver):
    while(not noActiveAjax(driver)):
        time.sleep(1)

class CsrfTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        user, created = ESPUser.objects.get_or_create(username='student', first_name='Student', last_name='Student')
        user.set_password('student')
        user.save()

        # Save the last good version of the template override in question
        if len(TemplateOverride.objects.filter(name='index.html')) == 0:
             # There are no existing template overrides
             self.good_version = -1
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
             self.good_version = to.next_version() - 1

    def setUpNormalLogin(self):
        if(self.good_version == -1):
             to, created = TemplateOverride.objects.get_or_create(name='index.html', version=1)
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
        to.content = """
{% extends "elements/html" %}

{% block body %}
<div id="login_box">
<div class="corners"><div class="ul"></div><div class="ur"></div><div class="dl"></div><div class="dr"></div></div>
<div id="login_div">
{% if not request.user.is_authenticated %}
<!-- login -->
<form name="login_form" id="login_form" method="post" action="/myesp/login/">{% csrf_token %}
  <input type="hidden" name="next" value="/" />
  <input type="text" id="login_user" name="username"/>
  <input type="password" id="login_pswd" name="password" />
  <input type="submit" id="login_submit" name="login_submit" value="" />
  <a href="/myesp/register" id="login_signup"></a>
  <a href="/myesp/loginhelp.html" id="login_help">need help?</a>
</form>

{% else %}
<!-- logout -->
  Hello, {{ request.user.first_name }} {{ request.user.last_name }}!<br />
  (<a href="/myesp/signout/">Logout</a>)
{% endif %}

</div>
</div>
{% endblock %}
"""
        to.save()
    def setUpAjaxLogin(self):
        if(self.good_version == -1):
             to, created = TemplateOverride.objects.get_or_create(name='index.html', version=1)
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
        to.content = """
{% extends "elements/html" %}

{% block body %}
<script type="text/javascript" src="/media/scripts/ajax_tools.js"></script>
<script type="text/javascript">
    register_form({id: "loginform", url: "/myesp/ajax_login/"});
</script>


<div id="loginbox" >
<table align="center" class="loginform" cellspacing="0" cellpadding="5">
<tr><td>

{% if login_result %}
    <div class="navbar"><center><span style="color: #BCCAF5;">{{ login_result }}</span></center><br /></div>
{% else %}
    {% if not request.user.is_authenticated %}
        <div class="navbar">Please log in to access program registration<br /></div>
    {% endif %}
{% endif %}

{% if request.user.is_authenticated %}
<div id="divnav">
  <p align="center">
    Hello, {{ request.user.first_name }} {{ request.user.last_name }}!<br />
    {% if request.user.is_staff %}
        <a href="/admin/">Administration pages</a> <br />
    {% endif %}
    {% if request.user.isAdministrator %}
        <a href="/manage/programs/">Manage Programs</a> <br />
    {% endif %}
    {% if request.user.other_user %}
        <br /><a href="/myesp/switchback/">Unmorph to {{ request.session.user_morph.olduser_name }}</a> <br />({{ request.session.user_morph.retTitle }})<br /><br />
    {% endif %}
    <a href="/myesp/signout/">Logout</a>
  </p>
</div>
{% else %}

<div id="divnav">
  <form name="loginform" id="loginform" method="post" action="/myesp/login/">{% csrf_token %}
    <input type="hidden" name="next" value="{{ request.path }}" />
    <table border="0" cellpadding="0" cellspacing="0" summary=" ">
      <tr>
        <td><div class="divformcol1"><label for="user">User name:</label></div></td>
        <td><div class="divformcol2"><input type="text" id="id_username" name="username" id="user" size="8" value="" maxlength="255" class="inputbox" /></div></td>

        <td><div class="divformcol3">&nbsp;</div></td>
      </tr>
      <tr>
        <td><div class="divformcol1"><label for="pass">Password:</label></div></td>
        <td><div class="divformcol2"><input type="password" id="id_password" name="password" id="pass" size="8" value="" maxlength="255" class="inputbox" /></div></td>
        <td><div class="divformcol3"><input type="image" name="gologin" id="gologin" src="/media/images/go.gif" class="gobutton" alt="Go" title=""/></div></td>
      </tr>
      <tr>

        <td colspan="3"><div class="divformcol1"><a href="/myesp/loginhelp.html">Login Help</a>
        <span style="padding-left: 25px;">
        <a href="/myesp/register">Register</a></span></div></td>
      </tr>
    </table>
  </form>
</div>
{% endif %}

</td></tr>
</table>
</div>
{% endblock %}
"""
        to.save()

    def tearDown(self):
        if (self.good_version > 1):
            # Tear down the template override for consistent behavior
            last_good_to = TemplateOverride.objects.filter(name='index.html', version=self.good_version)
            last_good_to.save()
        else:
            # We need to get rid of the template override entirely
            TemplateOverride.objects.filter(name='index.html').delete()

    def try_login(self):
        elem = self.find_element_by_name("username") # Find the username field
        elem.send_keys("student")
        elem = self.find_element_by_name("password") # Find the password field
        elem.send_keys("student")
        elem.submit()

    def try_normal_login(self):
        self.try_login()
        self.open_url("/")

    def try_ajax_login(self):
        self.try_login()
        try:
            WebDriverWait(self, 10).until(noActiveAjax)
        except:
            stderr.write(str(exc_info()[0]) + "\n")
            stderr.write("Wait for ajax login timed out.\n")
        self.open_url("/")

    def logout(self):
        self.open_url("/myesp/signout/")
        self.open_url("/")

    def test_csrf_delete(self):
        # First set up and test AJAX
        self.setUpAjaxLogin()

        self.open_url("/")
        self.try_ajax_login()
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()

        self.delete_cookie("csrftoken")

        self.try_ajax_login()
        self.failUnless(self.is_text_present('Please log in to access program registration'))
        self.logout()

        self.try_ajax_login()
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()


        # Now set up and test normal login
        self.setUpNormalLogin()
        self.open_url("/") # Load index

        self.try_normal_login()
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()

        self.delete_cookie("csrftoken")

        self.try_normal_login()
        self.failUnless(self.is_element_present('#login_box'))
        self.logout()

        self.try_normal_login()
        self.failUnless(self.is_text_present('Student Student'))
        self.logout()

        self.close()
