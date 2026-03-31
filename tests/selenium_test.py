def test_makeaclass_form_submission(self):
    self.driver.get(self.live_server_url + reverse("makeaclass"))
    
    # wait for input
    WebDriverWait(self.driver, 10).until(
        EC.presence_of_element_located((By.NAME, "classname"))
    )
    
    name_input = self.driver.find_element("name", "classname")
    name_input.send_keys("Test Class")
    
    subject_input = self.driver.find_element("name", "subject")
    subject_input.send_keys("Math")
    
    submit_button = self.driver.find_element("name", "submit")
    submit_button.click()
    
    # check success
    self.assertIn("success", self.driver.page_source)
