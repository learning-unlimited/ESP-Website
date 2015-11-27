#!/usr/bin/python

import warnings
import atexit

from esp.utils.with_runserver import with_runserver

class SeleniumDriverHandler(object):
    """ A class that loads all available Selenium drivers (ie., browsers) at startup. """
    _instances = {}

    try:
        from selenium import webdriver
    except ImportError:
        webdriver = False

    if webdriver:
        for name, fn in {'firefox': webdriver.Firefox, 'chrome': webdriver.Chrome, 'IE': webdriver.Ie}.iteritems():
            try:
                driver = fn()
                _instances[name] = driver
            except:
                pass

    if len(_instances) == 0:
        warnings.warn("No Selenium browsers available!  Selenium tests will all pass without executing.", RuntimeWarning)

    def _closeAll(instances):
        for i in instances.itervalues():
            try:
                i.close()
            except:
                pass

    atexit.register(_closeAll, _instances)

    @classmethod
    def getDrivers(cls):
        return cls._instances.values()

    @classmethod
    def listAvailableDrivers(cls):
        return cls._instances.names()

    @classmethod
    def getDriver(cls, name):
        return cls._instances[name]



def selenium_test(fn):
    """
    Decorator; takes a function of two argument,
    a Selenium driver and a server URL,
    and returns a function of no argumentsthat calls the
    first function iteratively with each available driver.
    """
    @with_runserver
    def _wrapped(url):
        for driver in SeleniumDriverHandler.getDrivers():
            fn(driver, url)

    return _wrapped

## And here's how to use this decorator:
## (Probably as part of a PyUnit test, but, eh, really anywhere works.)
@selenium_test
def test_sample_selenium(driver, uri):
    driver.get(uri)

if __name__ == "__main__":
    test_sample_selenium()
