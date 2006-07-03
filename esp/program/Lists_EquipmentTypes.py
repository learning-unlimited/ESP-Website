from esp.program.models import EquipmentType

EquipmentTypeOptions = (
    # Format is: ('Name', NumberOfItemAvailable),
    ('Projector', 4),
    ('Classroom with Desks', 10),
    ('Athena lab', 3),
    ('Classroom with working space for students',  15),
    )

def populate():
	for eq_stuff in EquipmentTypeOptions:
	    if EquipmentType.objects.filter(equipment=eq_stuff[0]).count() == 0:
	        e = EquipmentType()
	        e.equipment = eq_stuff[0]
	        e.numAvailable = eq_stuff[1]
