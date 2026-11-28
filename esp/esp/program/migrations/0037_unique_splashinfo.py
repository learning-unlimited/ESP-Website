from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('program', '0036_printer_setup_module_title'),
    ]

    operations = [
        # Keep the lowest ID for each set of identical rows. If any pair has
        # differing values, adding the constraint fails and rolls back the
        # cleanup so the conflicting records can be reviewed.
        migrations.RunSQL(
            [
                'LOCK TABLE program_splashinfo IN ACCESS EXCLUSIVE MODE',
                """
                DELETE FROM program_splashinfo AS info
                USING (
                    SELECT id, row_number() OVER (
                        PARTITION BY student_id, program_id, lunchsat, lunchsun,
                                     siblingdiscount, siblingname, submitted
                        ORDER BY id
                    ) AS duplicate_number
                    FROM program_splashinfo
                    WHERE program_id IS NOT NULL
                ) AS ranked
                WHERE info.id = ranked.id AND ranked.duplicate_number > 1
                """,
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterUniqueTogether(
            name='splashinfo',
            unique_together={('student', 'program')},
        ),
    ]
