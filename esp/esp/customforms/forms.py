from django.forms.fields import Select

class CourseSelect(Select):
	"""A select widget with courses related to a particular program as its choices"""
	def __init__(self, program=None, attrs=None):
		courses=program.classsubject_set.all()
		choices=[]
		for course in courses:
			course_title=course.title()
			choices.append((course_title, course_title))
		super(CourseSelect, self).__init__(attrs, choices=choices)	
