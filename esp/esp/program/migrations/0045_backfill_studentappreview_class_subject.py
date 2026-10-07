from django.db import migrations


def backfill_class_subject(apps, schema_editor):
    """ Link a review to a class only where the reviewer teaches exactly one of
    the classes the application asked about; anything ambiguous stays null. """
    ClassSubject = apps.get_model('program', 'ClassSubject')
    StudentAppReview = apps.get_model('program', 'StudentAppReview')

    for review in StudentAppReview.objects.filter(class_subject__isnull=True).iterator():
        candidates = list(ClassSubject.objects.filter(
            studentappquestion__studentapplication__reviews=review,
            teachers=review.reviewer_id,
        ).distinct().values_list('id', flat=True)[:2])
        if len(candidates) == 1:
            review.class_subject_id = candidates[0]
            review.save(update_fields=['class_subject'])


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0044_studentappreview_class_subject'),
    ]

    operations = [
        #   Reverse is a noop: unmigrating 0044 drops the column anyway.
        migrations.RunPython(backfill_class_subject, migrations.RunPython.noop),
    ]
