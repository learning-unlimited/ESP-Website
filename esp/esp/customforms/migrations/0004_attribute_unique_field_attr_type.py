from django.db import migrations, models


def dedupe_attributes(apps, schema_editor):
    Attribute = apps.get_model('customforms', 'Attribute')
    seen = set()
    duplicate_ids = []
    for attr in Attribute.objects.order_by('field_id', 'attr_type', 'id').only('id', 'field_id', 'attr_type'):
        key = (attr.field_id, attr.attr_type)
        if key in seen:
            duplicate_ids.append(attr.id)
        else:
            seen.add(key)
    Attribute.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customforms', '0003_auto_20260306_0336'),
    ]

    operations = [
        migrations.RunPython(dedupe_attributes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='attribute',
            constraint=models.UniqueConstraint(fields=['field', 'attr_type'], name='unique_field_attr_type'),
        ),
    ]
