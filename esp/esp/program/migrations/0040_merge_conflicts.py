from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('program', '0037_auto_20260402_2109'),   # latest from one branch
        ('program', '0035_auto_20260326_1003'),   # from another branch
        ('program', '0034_auto_20260319_1454'),   # include all leaf nodes
    ]

    operations = []