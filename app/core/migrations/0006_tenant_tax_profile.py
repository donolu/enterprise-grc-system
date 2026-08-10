from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0005_tenant_email_verification")]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="billing_country",
            field=models.CharField(
                blank=True,
                help_text="ISO 3166-1 alpha-2 country code used for billing and tax calculation.",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="business_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("individual", "Individual"),
                    ("business", "Business"),
                    ("charity", "Charity"),
                    ("public_body", "Public body"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="tax_identifier",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="tenant",
            name="tax_identifier_type",
            field=models.CharField(
                blank=True,
                choices=[("vat", "VAT"), ("gst", "GST"), ("other", "Other")],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="tax_identifier_status",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("pending", "Pending"),
                    ("valid", "Valid"),
                    ("invalid", "Invalid"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="tax_identifier_validated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
