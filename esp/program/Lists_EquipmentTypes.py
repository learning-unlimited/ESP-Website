from esp.program.models import EquipmentTypes

EquipmentTypeOptions = (
    # Format is: ('Name', NumberOfItemAvailable),
    ('Projector', 4),
    ('Classroom with Desks', 10),
    ('Athena lab', 3),
    ('Classroom with working space for students',  15),
    )

for eq_stuff in EquipmentTypeOptions:
    if EquipmentTypes.objects.filter(equipment=eq_stuff[0]).count() == 0:
        e = EquipmentTypes()
        e.equipment = eq_stuff[0]
        e.numAvailable = eq_stuff[1]
        
        
