# Generated manually to fix implementation_status max_length

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='controlassessment',
            name='implementation_status',
            field=models.CharField(choices=[('not_implemented', 'Not Implemented'), ('partially_implemented', 'Partially Implemented'), ('implemented', 'Implemented'), ('not_applicable', 'Not Applicable')], default='not_implemented', help_text='Current implementation status of the control', max_length=25),
        ),
    ]