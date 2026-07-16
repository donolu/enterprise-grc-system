import os
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import override_settings
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from openpyxl import Workbook
from rest_framework import status
from rest_framework.test import APIClient

from core.models import AuditEvent
from .models import Asset, AssetReviewReminderLog
from .tasks import send_asset_review_reminders

User = get_user_model()


class AssetTenantTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.defaults['HTTP_HOST'] = self.domain.domain


class ImportAssetsCommandTest(AssetTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='asset.owner',
            email='asset.owner@example.com',
            password='testpass123',
            is_staff=True,
        )

    def create_asset_workbook(self, rows, sheet_name='Server'):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name
        for row in rows:
            worksheet.append(row)

        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        temp_file.close()
        workbook.save(temp_file.name)
        return temp_file.name

    def test_import_assets_is_idempotent_and_resolves_owner(self):
        temp_file = self.create_asset_workbook([
            [
                'Computer Name', 'Domain', 'IP Address', 'Last Successful Scan',
                'Username', 'Location', 'Manufacturer', 'Device Model',
                'Operating System', 'Serial Number', 'MAC Address',
                'Criticality', 'Owner', 'System Description', 'Comment',
            ],
            [
                'SRV-001', 'corp.local', '10.0.0.5', '2026-07-01',
                'svc.backup', 'London', 'Dell', 'PowerEdge', 'Ubuntu',
                'SN-001', 'AA:BB:CC:DD:EE:FF', 'High', self.user.email,
                'Backup server', 'Primary backup node',
            ],
        ])

        try:
            call_command('import_assets', temp_file, '--user', self.user.username)
            call_command('import_assets', temp_file, '--user', self.user.username)

            self.assertEqual(Asset.objects.count(), 1)
            asset = Asset.objects.get()
            self.assertEqual(asset.asset_id, 'SN-001')
            self.assertEqual(asset.name, 'SRV-001')
            self.assertEqual(asset.asset_type, 'server')
            self.assertEqual(asset.criticality, 'high')
            self.assertEqual(asset.owner, self.user)
            self.assertEqual(asset.owner_name, self.user.email)
            self.assertEqual(asset.source_sheet, 'Server')
            audit_events = AuditEvent.objects.filter(event='ASSET_REGISTER_IMPORTED')
            self.assertEqual(audit_events.count(), 2)
            audit_event = audit_events.first()
            self.assertEqual(audit_event.details['actor']['id'], str(self.user.id))
            self.assertEqual(audit_event.details['object']['type'], 'assets.Asset')
            self.assertEqual(audit_event.details['event'], 'ASSET_REGISTER_IMPORTED')
            self.assertEqual(audit_event.details['source']['type'], 'import')
        finally:
            os.unlink(temp_file)

    def test_import_assets_validates_required_headers(self):
        temp_file = self.create_asset_workbook([
            ['Serial Number', 'Owner'],
            ['SN-001', self.user.email],
        ])

        try:
            with self.assertRaises(CommandError):
                call_command('import_assets', temp_file, '--dry-run')
            self.assertEqual(Asset.objects.count(), 0)
        finally:
            os.unlink(temp_file)

    def test_admin_upload_endpoint_imports_asset_register(self):
        temp_file = self.create_asset_workbook([
            ['Asset Name', 'IP Address', 'Serial Number', 'Criticality', 'Owner'],
            ['Printer 01', '10.0.0.20', 'PRN-001', 'Medium', self.user.username],
        ], sheet_name='Printer')
        with open(temp_file, 'rb') as file:
            upload = SimpleUploadedFile(
                'asset-register.xlsx',
                file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

        try:
            self.client.force_authenticate(user=self.user)
            response = self.client.post(
                '/api/assets/assets/import-register/',
                {'file': upload, 'dry_run': 'false'},
                format='multipart',
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['imported_count'], 1)
            self.assertEqual(Asset.objects.get().asset_type, 'printer')
        finally:
            os.unlink(temp_file)


class AssetAPITest(AssetTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='asset.admin',
            email='asset.admin@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_asset_crud_api(self):
        response = self.client.post(
            '/api/assets/assets/',
            {
                'asset_id': 'ASSET-001',
                'name': 'Customer Database',
                'asset_type': 'database',
                'classification': 'restricted',
                'criticality': 'critical',
                'lifecycle_status': 'active',
                'owner': self.user.id,
                'location': 'Azure UK South',
                'next_review_date': '2026-08-01',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        asset_id = response.data['id']

        list_response = self.client.get('/api/assets/assets/?search=Customer')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['results'][0]['asset_id'], 'ASSET-001')

        detail_response = self.client.get(f'/api/assets/assets/{asset_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['classification'], 'restricted')

        patch_response = self.client.patch(
            f'/api/assets/assets/{asset_id}/',
            {'criticality': 'high'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['criticality'], 'high')

    def test_due_for_review_endpoint(self):
        Asset.objects.create(
            asset_id='ASSET-DUE',
            name='Due Asset',
            asset_type='server',
            owner=self.user,
            next_review_date=timezone.now().date(),
            created_by=self.user,
        )

        response = self.client.get('/api/assets/assets/due_for_review/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['asset_id'], 'ASSET-DUE')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AssetReminderTaskTest(AssetTenantTestCase):
    def setUp(self):
        super().setUp()
        self.owner = User.objects.create_user(
            username='asset.owner',
            email='asset.owner@example.com',
            password='testpass123',
        )

    @patch('assets.tasks.send_mail')
    def test_send_asset_review_reminders_logs_and_deduplicates(self, mock_send_mail):
        Asset.objects.create(
            asset_id='ASSET-REM',
            name='Reminder Asset',
            asset_type='server',
            owner=self.owner,
            next_review_date=timezone.now().date() + timedelta(days=7),
        )

        first_result = send_asset_review_reminders()
        second_result = send_asset_review_reminders()

        self.assertEqual(first_result, {'sent': 1})
        self.assertEqual(second_result, {'sent': 0})
        self.assertEqual(mock_send_mail.call_count, 1)
        self.assertEqual(AssetReviewReminderLog.objects.count(), 1)
