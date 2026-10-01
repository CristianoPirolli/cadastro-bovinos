from datetime import date

from django.db import migrations, models


def mark_past_second_doses(apps, schema_editor):
    Vaccine = apps.get_model('cadastro', 'Vaccine')
    Vaccine.objects.filter(second_dose=True, second_dose_date__lte=date.today()).update(second_dose_applied=True)


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0004_merge_20250910_2114'),
    ]

    operations = [
        migrations.AddField(
            model_name='vaccine',
            name='applied',
            field=models.BooleanField(default=True, verbose_name='aplicada'),
        ),
        migrations.AddField(
            model_name='vaccine',
            name='second_dose_applied',
            field=models.BooleanField(default=False, verbose_name='2ª dose aplicada'),
        ),
        migrations.RunPython(mark_past_second_doses, migrations.RunPython.noop),
    ]
