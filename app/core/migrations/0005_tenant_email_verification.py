from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_tenant_email_settings")]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="email_sender_verification_token_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="tenant",
            name="email_sender_verification_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
