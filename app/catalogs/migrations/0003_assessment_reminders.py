# Generated manually for assessment reminder functionality

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalogs', '0002_alter_controlassessment_implementation_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssessmentReminderConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enable_reminders', models.BooleanField(default=True, help_text='Whether to send automated reminders to this user')),
                ('advance_warning_days', models.PositiveIntegerField(default=7, help_text='Days before due date to send first reminder')),
                ('overdue_reminders', models.BooleanField(default=True, help_text='Whether to send reminders for overdue assessments')),
                ('reminder_frequency', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('custom', 'Custom Days')], default='daily', help_text='How frequently to send overdue reminders', max_length=10)),
                ('custom_reminder_days', models.JSONField(blank=True, default=list, help_text='Custom days for reminders (e.g., [1, 3, 7] for 1, 3, and 7 days before)')),
                ('email_notifications', models.BooleanField(default=True, help_text='Whether to send email notifications')),
                ('include_assessment_details', models.BooleanField(default=True, help_text='Whether to include detailed assessment information in emails')),
                ('include_remediation_items', models.BooleanField(default=True, help_text='Whether to include remediation due dates in reminders')),
                ('daily_digest_enabled', models.BooleanField(default=False, help_text='Whether to send daily digest of all upcoming/overdue items')),
                ('weekly_digest_enabled', models.BooleanField(default=True, help_text='Whether to send weekly digest of upcoming assessments')),
                ('digest_day_of_week', models.PositiveIntegerField(default=1, help_text='Day of week for weekly digest (0=Sunday, 1=Monday, etc.)')),
                ('silence_completed_assessments', models.BooleanField(default=True, help_text='Stop sending reminders for completed assessments')),
                ('silence_not_applicable', models.BooleanField(default=True, help_text="Don't send reminders for assessments marked as not applicable")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(help_text='User for whom reminders are configured', on_delete=django.db.models.deletion.CASCADE, related_name='reminder_config', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Assessment Reminder Configuration',
                'verbose_name_plural': 'Assessment Reminder Configurations',
            },
        ),
        migrations.CreateModel(
            name='AssessmentReminderLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reminder_type', models.CharField(choices=[('advance_warning', 'Advance Warning'), ('due_today', 'Due Today'), ('overdue', 'Overdue'), ('weekly_digest', 'Weekly Digest'), ('daily_digest', 'Daily Digest')], max_length=20)),
                ('days_before_due', models.IntegerField(blank=True, help_text='Days before due date when reminder was sent (negative for overdue)', null=True)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('email_sent', models.BooleanField(default=False)),
                ('assessment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminder_logs', to='catalogs.controlassessment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assessment_reminder_logs', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='assessmentreminderlog',
            index=models.Index(fields=['assessment', 'user'], name='catalogs_as_assessm_bf1bb5_idx'),
        ),
        migrations.AddIndex(
            model_name='assessmentreminderlog',
            index=models.Index(fields=['sent_at'], name='catalogs_as_sent_at_b04c9f_idx'),
        ),
        migrations.AddIndex(
            model_name='assessmentreminderlog',
            index=models.Index(fields=['reminder_type'], name='catalogs_as_reminde_068c8b_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='assessmentreminderlog',
            unique_together={('assessment', 'user', 'reminder_type', 'days_before_due')},
        ),
    ]