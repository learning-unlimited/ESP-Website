# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def backfill_class_subject(apps, schema_editor):
    """
    Backfill StudentAppReview.class_subject for existing reviews.
    
    Strategy: Find the class_subject from the StudentApplication's related
    StudentAppQuestion that matches this review, or leave NULL if no match found.
    
    Since reviews are associated with StudentApplication via ManyToMany,
    we infer the class_subject from the first matching question in the app.
    """
    StudentAppReview = apps.get_model('program', 'StudentAppReview')
    StudentApplication = apps.get_model('program', 'StudentApplication')
    
    backfilled_count = 0
    unfilled_count = 0
    
    # Get all reviews that don't have a class_subject yet
    reviews_without_class = StudentAppReview.objects.filter(class_subject__isnull=True)
    
    for review in reviews_without_class:
        # Find StudentApplications that contain this review
        apps_with_review = StudentApplication.objects.filter(reviews=review)
        
        if apps_with_review.exists():
            app = apps_with_review.first()
            # Try to get a question from this app that has a subject
            questions_with_subject = app.questions.filter(subject__isnull=False)
            
            if questions_with_subject.exists():
                question = questions_with_subject.first()
                if question.subject:
                    review.class_subject = question.subject
                    review.save()
                    backfilled_count += 1
                else:
                    unfilled_count += 1
            else:
                unfilled_count += 1
        else:
            unfilled_count += 1
    
    print(f"\nBackfill Complete:")
    print(f"  - Reviews backfilled with class_subject: {backfilled_count}")
    print(f"  - Reviews left NULL (no associated class): {unfilled_count}")
    print(f"  - Total reviews processed: {backfilled_count + unfilled_count}\n")


def reverse_backfill(apps, schema_editor):
    """
    Reverse by setting class_subject back to NULL.
    This is safe since we're only reverting to the previous state.
    """
    StudentAppReview = apps.get_model('program', 'StudentAppReview')
    StudentAppReview.objects.all().update(class_subject=None)
    print("\nReverse: All class_subject fields cleared.\n")


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0034_studentappreview_class_subject'),
    ]

    operations = [
        migrations.RunPython(backfill_class_subject, reverse_backfill),
    ]
