from django.db import migrations, models
from django.db.models import Count, Max


def dedupe_attributes(apps, schema_editor):
    Attribute = apps.get_model('customforms', 'Attribute')
    # Keep the newest row of each duplicated (field, attr_type) pair.
    duplicates = (Attribute.objects.values('field_id', 'attr_type')
                  .annotate(n=Count('id'), keep_id=Max('id'))
                  .filter(n__gt=1))
    for dup in duplicates:
        Attribute.objects.filter(field_id=dup['field_id'], attr_type=dup['attr_type']) \
            .exclude(id=dup['keep_id']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customforms', '0005_fix_link_field_column_names'),
    ]

    operations = [
        migrations.RunPython(dedupe_attributes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='attribute',
            constraint=models.UniqueConstraint(fields=['field', 'attr_type'], name='unique_field_attr_type'),
        ),
    ]
