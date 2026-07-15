import uuid

from django.conf import settings
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
            name='CalendarEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('event_type', models.CharField(choices=[('deadline', 'Deadline'), ('review', 'Review'), ('meeting', 'Meeting'), ('training', 'Training'), ('custom', 'Custom')], default='deadline', max_length=30)),
                ('due_date', models.DateField()),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='scheduled', max_length=20)),
                ('source_url', models.CharField(blank=True, max_length=500)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_calendar_events', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='calendar_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['due_date', 'title'],
            },
        ),
        migrations.CreateModel(
            name='CalendarNotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_enabled', models.BooleanField(default=True)),
                ('advance_reminder_days', models.PositiveIntegerField(default=7)),
                ('due_date_enabled', models.BooleanField(default=True)),
                ('overdue_enabled', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='calendar_notification_preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CalendarReminderLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_type', models.CharField(max_length=50)),
                ('source_id', models.CharField(max_length=80)),
                ('title', models.CharField(max_length=255)),
                ('due_date', models.DateField()),
                ('reminder_type', models.CharField(choices=[('advance_warning', 'Advance warning'), ('due_today', 'Due today'), ('overdue', 'Overdue')], max_length=30)),
                ('sent_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('email_sent', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calendar_reminder_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-sent_at'],
                'unique_together': {('source_type', 'source_id', 'recipient', 'due_date', 'reminder_type')},
            },
        ),
        migrations.CreateModel(
            name='CalendarAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('created', 'Created'), ('updated', 'Updated'), ('deleted', 'Deleted'), ('reminder_sent', 'Reminder sent')], max_length=30)),
                ('source_type', models.CharField(blank=True, max_length=50)),
                ('source_id', models.CharField(blank=True, max_length=80)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='calendar_audit_logs', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='calendarhub.calendarevent')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['due_date', 'status'], name='calendarhub_due_dat_0093ce_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['owner', 'due_date'], name='calendarhub_owner_i_36381a_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['event_type'], name='calendarhub_event_t_b1e070_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarreminderlog',
            index=models.Index(fields=['source_type', 'source_id'], name='calendarhub_source__c4d63f_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarreminderlog',
            index=models.Index(fields=['recipient', 'sent_at'], name='calendarhub_recipie_cc86b3_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarreminderlog',
            index=models.Index(fields=['due_date', 'reminder_type'], name='calendarhub_due_dat_c9d159_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarauditlog',
            index=models.Index(fields=['action', 'created_at'], name='calendarhub_action_ced330_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarauditlog',
            index=models.Index(fields=['source_type', 'source_id'], name='calendarhub_source__643022_idx'),
        ),
    ]
