# Generated manually due to migration conflict
# Risk management initial migration

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RiskCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('color', models.CharField(default='#6B7280', help_text='Hex color code for UI display', max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Risk Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='RiskMatrix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('is_default', models.BooleanField(default=False)),
                ('impact_levels', models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(3), django.core.validators.MaxValueValidator(7)])),
                ('likelihood_levels', models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(3), django.core.validators.MaxValueValidator(7)])),
                ('matrix_config', models.JSONField(default=dict, help_text='Matrix configuration mapping impact x likelihood to risk levels')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_risk_matrices', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Risk Matrices',
                'ordering': ['-is_default', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Risk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('risk_id', models.CharField(help_text='Unique risk identifier', max_length=50, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('impact', models.PositiveIntegerField(help_text='Impact level (1=Very Low, 5=Very High)', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('likelihood', models.PositiveIntegerField(help_text='Likelihood level (1=Very Low, 5=Very High)', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('risk_level', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], help_text='Calculated risk level', max_length=20)),
                ('status', models.CharField(choices=[('identified', 'Identified'), ('assessed', 'Assessed'), ('treatment_planned', 'Treatment Planned'), ('treatment_in_progress', 'Treatment in Progress'), ('mitigated', 'Mitigated'), ('accepted', 'Accepted'), ('transferred', 'Transferred'), ('closed', 'Closed')], default='identified', max_length=30)),
                ('treatment_strategy', models.CharField(blank=True, choices=[('mitigate', 'Mitigate'), ('accept', 'Accept'), ('transfer', 'Transfer'), ('avoid', 'Avoid')], max_length=20)),
                ('treatment_description', models.TextField(blank=True, help_text='Description of the treatment approach')),
                ('identified_date', models.DateField(default=django.utils.timezone.now)),
                ('last_assessed_date', models.DateField(blank=True, null=True)),
                ('next_review_date', models.DateField(blank=True, null=True)),
                ('closed_date', models.DateField(blank=True, null=True)),
                ('potential_impact_description', models.TextField(blank=True, help_text='Detailed description of potential impact')),
                ('current_controls', models.TextField(blank=True, help_text='Existing controls or mitigations in place')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='risks', to='risk.riskcategory')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_risks', to=settings.AUTH_USER_MODEL)),
                ('risk_matrix', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='risk.riskmatrix')),
                ('risk_owner', models.ForeignKey(blank=True, help_text='Person responsible for managing this risk', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_risks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-risk_level', '-impact', '-likelihood', 'title'],
            },
        ),
        migrations.CreateModel(
            name='RiskNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField()),
                ('note_type', models.CharField(choices=[('general', 'General'), ('assessment', 'Assessment'), ('treatment', 'Treatment'), ('review', 'Review'), ('status_change', 'Status Change')], default='general', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='risk_notes', to=settings.AUTH_USER_MODEL)),
                ('risk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='risk.risk')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='risk',
            index=models.Index(fields=['status', 'risk_level'], name='risk_risk_status_b23a15_idx'),
        ),
        migrations.AddIndex(
            model_name='risk',
            index=models.Index(fields=['risk_owner', 'status'], name='risk_risk_risk_ow_4a1234_idx'),
        ),
        migrations.AddIndex(
            model_name='risk',
            index=models.Index(fields=['next_review_date'], name='risk_risk_next_re_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='risk',
            index=models.Index(fields=['category', 'risk_level'], name='risk_risk_categor_789abc_idx'),
        ),
    ]