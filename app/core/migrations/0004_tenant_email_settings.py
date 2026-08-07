from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_alter_auditevent_options_and_more")]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="email_sender_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="tenant",
            name="email_sender_address",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="tenant",
            name="email_reply_to",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="tenant",
            name="email_sender_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
