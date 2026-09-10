from django.db import migrations


def backfill_class_subject(apps, schema_editor):
    """ Point existing reviews at a class where that class is unambiguous.

    A review is only linked to a class if the reviewer teaches exactly one of
    the classes that the reviewed application asked questions about.  Reviews
    by program directors, and reviews by teachers of several of the applied-to
    classes, are left null rather than guessed at: `getRankInClass` feeds
    admissions decisions, so a wrong class is worse than no class.
    """
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
        #   Not reversible on its own: unmigrating 0044 drops the column, and
        #   nulling every class_subject would also discard the ones set by
        #   application code after this ran.
        migrations.RunPython(backfill_class_subject, migrations.RunPython.noop),
    ]
