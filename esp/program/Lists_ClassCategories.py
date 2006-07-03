from esp.program.models import ClassCategories

ClassCategoryOptions = (
    'Computer Science',
    'Hobbies',
    'Liberal Arts',
    'Mathematics',
    'Performing Arts',
    'Science',
    'Zocial Zcience',
    )

def populate():
	for c_desc in ClassCategoryOptions:
	    if ClassCategories.objects.filter(category=c_desc).count() == 0:
	        c = ClassCategories()
	        c.category = c_desc
	        c.save()
