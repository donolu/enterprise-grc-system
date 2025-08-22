# Generated manually for catalogs initial migration
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_document_documentaccess_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Framework',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Framework name (e.g., SOC 2 Type II)', max_length=200)),
                ('short_name', models.CharField(help_text='Short identifier (e.g., SOC2)', max_length=50)),
                ('description', models.TextField(help_text='Framework description and purpose')),
                ('framework_type', models.CharField(choices=[('security', 'Security Framework'), ('privacy', 'Privacy Framework'), ('financial', 'Financial Framework'), ('operational', 'Operational Framework'), ('industry', 'Industry-Specific Framework'), ('custom', 'Custom Framework')], default='security', max_length=20)),
                ('external_id', models.CharField(blank=True, help_text='External framework identifier or reference code', max_length=100, null=True)),
                ('issuing_organization', models.CharField(help_text='Organization that issued/maintains this framework', max_length=200)),
                ('official_url', models.URLField(blank=True, help_text='Official framework documentation URL', null=True)),
                ('version', models.CharField(default='1.0', help_text='Framework version', max_length=50)),
                ('effective_date', models.DateField(help_text='Date when this version became effective')),
                ('expiry_date', models.DateField(blank=True, help_text='Date when this version expires', null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('deprecated', 'Deprecated'), ('archived', 'Archived')], default='draft', max_length=20)),
                ('is_mandatory', models.BooleanField(default=False, help_text='Whether compliance with this framework is mandatory for the organization')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('imported_from', models.CharField(blank=True, help_text='Source of framework import (file, API, manual entry)', max_length=200)),
                ('import_checksum', models.CharField(blank=True, help_text='Checksum for tracking changes in imported frameworks', max_length=64)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_frameworks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name', '-version'],
                'indexes': [
                    models.Index(fields=['status', 'framework_type'], name='catalogs_fr_status_82b6c3_idx'),
                    models.Index(fields=['short_name'], name='catalogs_fr_short_n_0c5ac8_idx'),
                    models.Index(fields=['is_mandatory', 'status'], name='catalogs_fr_is_mand_7c64c9_idx'),
                ],
                'unique_together': {('name', 'version')},
            },
        ),
        migrations.CreateModel(
            name='Clause',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clause_id', models.CharField(help_text='Framework-specific clause identifier (e.g., CC6.1, A.8.2.1)', max_length=50)),
                ('title', models.CharField(help_text='Clause title or heading', max_length=300)),
                ('description', models.TextField(help_text='Full clause text and requirements')),
                ('sort_order', models.PositiveIntegerField(default=0, help_text='Display order within framework')),
                ('clause_type', models.CharField(choices=[('control', 'Control Requirement'), ('policy', 'Policy Requirement'), ('procedure', 'Procedure Requirement'), ('documentation', 'Documentation Requirement'), ('assessment', 'Assessment Requirement'), ('monitoring', 'Monitoring Requirement'), ('reporting', 'Reporting Requirement')], default='control', max_length=20)),
                ('criticality', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=10)),
                ('is_testable', models.BooleanField(default=True, help_text='Whether this clause can be tested/audited')),
                ('implementation_guidance', models.TextField(blank=True, help_text='Guidance on how to implement this clause')),
                ('testing_procedures', models.TextField(blank=True, help_text='Procedures for testing compliance with this clause')),
                ('external_references', models.JSONField(blank=True, default=dict, help_text='References to other standards, regulations, or frameworks')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('framework', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clauses', to='catalogs.framework')),
                ('parent_clause', models.ForeignKey(blank=True, help_text='Parent clause for hierarchical organization', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subclauses', to='catalogs.clause')),
            ],
            options={
                'ordering': ['framework', 'sort_order', 'clause_id'],
                'indexes': [
                    models.Index(fields=['framework', 'sort_order'], name='catalogs_cl_framewo_37be5b_idx'),
                    models.Index(fields=['clause_type', 'criticality'], name='catalogs_cl_clause__b9c69b_idx'),
                    models.Index(fields=['is_testable'], name='catalogs_cl_is_test_b652b0_idx'),
                ],
                'unique_together': {('framework', 'clause_id')},
            },
        ),
        migrations.CreateModel(
            name='Control',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Control name or title', max_length=200)),
                ('description', models.TextField(help_text='Detailed control description')),
                ('control_id', models.CharField(help_text='Unique control identifier', max_length=50, unique=True, validators=[django.core.validators.RegexValidator(message='Control ID must start with alphanumeric and contain only uppercase letters, numbers, hyphens, and dots', regex='^[A-Z0-9][A-Z0-9\\-\\.]*$')])),
                ('control_type', models.CharField(choices=[('preventive', 'Preventive Control'), ('detective', 'Detective Control'), ('corrective', 'Corrective Control'), ('compensating', 'Compensating Control'), ('administrative', 'Administrative Control'), ('technical', 'Technical Control'), ('physical', 'Physical Control')], max_length=20)),
                ('automation_level', models.CharField(choices=[('manual', 'Manual Control'), ('semi_automated', 'Semi-Automated Control'), ('automated', 'Automated Control'), ('continuous', 'Continuous Monitoring')], default='manual', max_length=20)),
                ('status', models.CharField(choices=[('planned', 'Planned'), ('in_progress', 'In Progress'), ('implemented', 'Implemented'), ('testing', 'Under Testing'), ('active', 'Active'), ('remediation', 'Needs Remediation'), ('disabled', 'Disabled'), ('retired', 'Retired')], default='planned', max_length=20)),
                ('business_owner', models.CharField(blank=True, help_text='Business unit or department responsible', max_length=200)),
                ('implementation_details', models.TextField(blank=True, help_text='Specific implementation steps and procedures')),
                ('frequency', models.CharField(blank=True, help_text='How often this control is performed (e.g., daily, monthly, annually)', max_length=100)),
                ('last_tested_date', models.DateField(blank=True, null=True)),
                ('last_test_result', models.CharField(blank=True, choices=[('not_effective', 'Not Effective'), ('partially_effective', 'Partially Effective'), ('largely_effective', 'Largely Effective'), ('fully_effective', 'Fully Effective')], max_length=20)),
                ('effectiveness_rating', models.CharField(blank=True, choices=[('not_effective', 'Not Effective'), ('partially_effective', 'Partially Effective'), ('largely_effective', 'Largely Effective'), ('fully_effective', 'Fully Effective')], help_text='Current effectiveness assessment', max_length=20)),
                ('evidence_requirements', models.TextField(blank=True, help_text='What evidence is needed to demonstrate this control\'s effectiveness')),
                ('documentation_links', models.JSONField(blank=True, default=list, help_text='Links to related policies, procedures, and documentation')),
                ('risk_rating', models.CharField(blank=True, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], help_text='Risk level if this control fails', max_length=10)),
                ('remediation_plan', models.TextField(blank=True, help_text='Plan for addressing control deficiencies')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('version', models.CharField(default='1.0', max_length=20)),
                ('change_log', models.JSONField(blank=True, default=list, help_text='History of changes to this control')),
                ('clauses', models.ManyToManyField(help_text='Framework clauses this control addresses', related_name='controls', to='catalogs.clause')),
                ('control_owner', models.ForeignKey(help_text='Person responsible for this control', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_controls', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_controls', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['control_id', 'name'],
                'indexes': [
                    models.Index(fields=['status', 'control_type'], name='catalogs_co_status_d7a71a_idx'),
                    models.Index(fields=['control_owner'], name='catalogs_co_control_73be2d_idx'),
                    models.Index(fields=['automation_level'], name='catalogs_co_automat_bb9dbd_idx'),
                    models.Index(fields=['last_tested_date'], name='catalogs_co_last_te_f7b81e_idx'),
                    models.Index(fields=['effectiveness_rating'], name='catalogs_co_effecti_bf5b6e_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ControlEvidence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Evidence title or description', max_length=200)),
                ('evidence_type', models.CharField(choices=[('document', 'Document/Policy'), ('screenshot', 'Screenshot'), ('log_file', 'Log File'), ('report', 'Report'), ('certificate', 'Certificate'), ('approval', 'Approval/Sign-off'), ('test_result', 'Test Result'), ('meeting_notes', 'Meeting Notes'), ('other', 'Other')], max_length=20)),
                ('description', models.TextField(blank=True, help_text='Additional evidence description')),
                ('external_url', models.URLField(blank=True, help_text='External URL for evidence (e.g., system screenshot)', null=True)),
                ('evidence_date', models.DateField(default=django.utils.timezone.now, help_text='Date when evidence was created or collected')),
                ('is_validated', models.BooleanField(default=False, help_text='Whether evidence has been validated')),
                ('validated_at', models.DateTimeField(blank=True, null=True)),
                ('validation_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('collected_by', models.ForeignKey(help_text='Person who collected this evidence', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('control', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evidence', to='catalogs.control')),
                ('document', models.ForeignKey(blank=True, help_text='Associated document file', null=True, on_delete=django.db.models.deletion.CASCADE, to='core.document')),
                ('validated_by', models.ForeignKey(blank=True, help_text='Person who validated this evidence', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='validated_evidence', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-evidence_date', '-created_at'],
                'indexes': [
                    models.Index(fields=['control', '-evidence_date'], name='catalogs_co_control_00f4e4_idx'),
                    models.Index(fields=['evidence_type'], name='catalogs_co_evidenc_df63bc_idx'),
                    models.Index(fields=['is_validated'], name='catalogs_co_is_vali_f00e8c_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='FrameworkMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mapping_type', models.CharField(choices=[('equivalent', 'Equivalent Requirements'), ('partial', 'Partially Overlapping'), ('supports', 'Supporting Requirement'), ('related', 'Related Requirement')], max_length=20)),
                ('mapping_rationale', models.TextField(blank=True, help_text='Explanation of why these clauses are mapped together')),
                ('confidence_level', models.IntegerField(default=75, help_text='Confidence percentage (0-100) in this mapping')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('source_clause', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_mappings', to='catalogs.clause')),
                ('target_clause', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='target_mappings', to='catalogs.clause')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_mappings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['mapping_type'], name='catalogs_fr_mapping_a80b3d_idx'),
                    models.Index(fields=['confidence_level'], name='catalogs_fr_confide_71b69d_idx'),
                ],
                'unique_together': {('source_clause', 'target_clause')},
            },
        ),
    ]