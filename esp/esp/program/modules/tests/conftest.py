# This conftest.py tells pytest to collect test classes from all .py files
# in this directory, even though they don't use the test_*.py naming convention.
# The files here are named after the module they test (e.g. programprintables.py)
# and were designed for Django's test runner which discovers TestCase subclasses
# regardless of filename.
collect_ignore = ["__init__.py", "support"]
