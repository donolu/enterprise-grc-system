import hashlib
import mimetypes
import posixpath
import re
import zipfile
from datetime import datetime
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalogs.models import Framework, TemplateDocument
from core.audit import log_audit_event
from core.models import Document

User = get_user_model()


class Command(BaseCommand):
    help = 'Import Axim template and sample documents from a ZIP file or single file'

    allowed_extensions = {
        '.csv', '.doc', '.docx', '.pdf', '.ppt', '.pptx', '.txt', '.xls',
        '.xlsx',
    }

    def add_arguments(self, parser):
        parser.add_argument('source_path', type=str, help='Path to a template library ZIP file or single document')
        parser.add_argument(
            '--user',
            type=str,
            default='system',
            help='Username to attribute imported documents to',
        )
        parser.add_argument(
            '--framework',
            type=str,
            help='Framework name or short name to link framework-specific templates to',
        )
        parser.add_argument(
            '--framework-version',
            dest='framework_version',
            type=str,
            help='Framework version to use with --framework',
        )
        parser.add_argument(
            '--module',
            type=str,
            choices=[choice[0] for choice in TemplateDocument.MODULE_CHOICES],
            help='Module classification for a single-file import',
        )
        parser.add_argument(
            '--document-type',
            type=str,
            choices=[choice[0] for choice in TemplateDocument.DOCUMENT_TYPE_CHOICES],
            help='Document type classification for a single-file import',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without storing documents',
        )

    def handle(self, *args, **options):
        source_path = Path(options['source_path'])
        if not source_path.exists():
            raise CommandError(f'File not found: {source_path}')

        user = self.get_import_user(options['user'])
        framework = self.get_framework(
            options.get('framework'),
            options.get('framework_version'),
        )
        entries = self.collect_entries(
            source_path,
            framework,
            module=options.get('module') or '',
            document_type=options.get('document_type') or '',
        )

        if options['dry_run']:
            self.show_dry_run_summary(entries)
            return

        with transaction.atomic():
            imported, updated = self.import_entries(source_path, entries, user)
            self.record_import_audit_event(
                source_path=source_path,
                entries=entries,
                user=user,
                imported=imported,
                updated=updated,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Imported {imported} template documents; updated {updated}.'
            )
        )

    def get_import_user(self, username):
        if username != 'system':
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User not found: {username}')

        user, created = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@localhost',
                'is_active': False,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
        return user

    def get_framework(self, framework_identifier, framework_version):
        if not framework_identifier:
            return None

        queryset = Framework.objects.filter(
            name=framework_identifier
        ) | Framework.objects.filter(short_name=framework_identifier)
        if framework_version:
            queryset = queryset.filter(version=framework_version)

        framework = queryset.order_by('-effective_date', '-version').first()
        if not framework:
            raise CommandError(
                f'Framework not found: {framework_identifier}'
                + (f' v{framework_version}' if framework_version else '')
            )
        return framework

    def collect_entries(self, source_path, framework, module='', document_type=''):
        if source_path.suffix.lower() == '.zip':
            return self.collect_zip_entries(source_path, framework)
        return self.collect_single_file_entry(source_path, framework, module, document_type)

    def collect_zip_entries(self, zip_path, framework):
        entries = []
        skipped = 0

        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                if self.should_skip(info):
                    skipped += 1
                    continue

                module, document_type = self.classify_path(info.filename)
                source_filename = posixpath.basename(info.filename)
                title = self.extract_title(source_filename)
                source_checksum = self.calculate_zip_entry_checksum(archive, info)
                document_code = self.extract_document_code(source_filename)
                linked_framework = self.link_framework(module, document_type, framework)

                entries.append({
                    'zip_info': info,
                    'title': title,
                    'module': module,
                    'document_type': document_type,
                    'document_code': document_code,
                    'version': self.extract_version(source_filename),
                    'framework': linked_framework,
                    'source_path': info.filename,
                    'source_filename': source_filename,
                    'source_checksum': source_checksum,
                    'source_modified_at': self.parse_zip_datetime(info),
                    'metadata': {
                        'zip_root': info.filename.split('/')[0],
                        'source_directory': posixpath.dirname(info.filename),
                        'file_extension': Path(source_filename).suffix.lower(),
                        'linkage_status': 'framework'
                        if linked_framework else 'unlinked',
                    },
                })

        self.skipped_count = skipped
        if not entries:
            raise CommandError('No importable template documents found in ZIP.')
        return entries

    def collect_single_file_entry(self, source_path, framework, module='', document_type=''):
        if source_path.name.startswith('~$') or source_path.name.startswith('.'):
            raise CommandError('Unsupported template file.')
        if source_path.suffix.lower() not in self.allowed_extensions:
            raise CommandError('Unsupported template file type.')

        inferred_module, inferred_document_type = self.classify_path(str(source_path))
        selected_module = module or inferred_module
        selected_document_type = document_type or inferred_document_type
        linked_framework = self.link_framework(selected_module, selected_document_type, framework)

        entry = {
            'title': self.extract_title(source_path.name),
            'module': selected_module,
            'document_type': selected_document_type,
            'document_code': self.extract_document_code(source_path.name),
            'version': self.extract_version(source_path.name),
            'framework': linked_framework,
            'source_path': str(source_path),
            'source_filename': source_path.name,
            'source_checksum': self.calculate_file_checksum(source_path),
            'source_modified_at': self.parse_file_modified_at(source_path),
            'metadata': {
                'source_directory': str(source_path.parent),
                'file_extension': source_path.suffix.lower(),
                'linkage_status': 'framework' if linked_framework else 'unlinked',
                'upload_mode': 'single_file',
            },
        }
        self.skipped_count = 0
        return [entry]

    def should_skip(self, info):
        if info.is_dir():
            return True

        parts = [part for part in info.filename.split('/') if part]
        filename = parts[-1] if parts else ''
        if any(part == '__MACOSX' for part in parts):
            return True
        if filename in {'.DS_Store', 'Thumbs.db'}:
            return True
        if filename.startswith('~$'):
            return True
        if filename.startswith('.'):
            return True
        return Path(filename).suffix.lower() not in self.allowed_extensions

    def classify_path(self, source_path):
        normalised = source_path.lower()

        if '/documentation module/policies/' in normalised:
            return 'policy', 'policy'
        if '/documentation module/standards/' in normalised:
            return 'standard', 'standard'
        if '/documentation module/procedure/' in normalised:
            return 'procedure', 'procedure'
        if '/iso 27001 mandatory documents module/' in normalised:
            return 'iso_mandatory', 'mandatory_document'
        if '/pci module/' in normalised:
            return 'pci', 'framework_spreadsheet'
        if '/risk register module/' in normalised:
            return 'risk', 'risk_register'
        if '/asset register module/' in normalised:
            return 'asset', 'asset_register'
        return 'other', 'template'

    def link_framework(self, module, document_type, framework):
        if framework and module in {'iso_mandatory', 'pci'}:
            return framework
        if framework and document_type == 'framework_spreadsheet':
            return framework
        return None

    def calculate_zip_entry_checksum(self, archive, info):
        sha256_hash = hashlib.sha256()
        with archive.open(info) as entry:
            for chunk in iter(lambda: entry.read(1024 * 1024), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def calculate_file_checksum(self, source_path):
        sha256_hash = hashlib.sha256()
        with source_path.open('rb') as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def parse_zip_datetime(self, info):
        try:
            naive = datetime(*info.date_time)
        except (TypeError, ValueError):
            return None
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def parse_file_modified_at(self, source_path):
        return datetime.fromtimestamp(
            source_path.stat().st_mtime,
            tz=timezone.get_current_timezone(),
        )

    def extract_title(self, filename):
        stem = Path(filename).stem
        stem = re.sub(r'^XXXX[-_\s]+', '', stem, flags=re.IGNORECASE)
        stem = re.sub(r'^[A-Z]{3}[-_\s]+ALL[-_\s]*\d+\s*[-_]*\s*', '', stem)
        stem = re.sub(r'\s+', ' ', stem.replace('_', ' ')).strip(' -')
        return stem[:255] or Path(filename).stem[:255]

    def extract_document_code(self, filename):
        match = re.search(
            r'(XXXX[-_\s]+[A-Z]{3}[-_\s]+ALL[-_\s]*\d+)',
            filename,
            flags=re.IGNORECASE,
        )
        if not match:
            return ''
        return re.sub(r'[-_\s]+', '-', match.group(1).upper())

    def extract_version(self, filename):
        match = re.search(r'\bv(?:ersion)?\s*([0-9]+(?:\.[0-9]+)*)\b', filename, re.IGNORECASE)
        return match.group(1) if match else ''

    def import_entries(self, source_path, entries, user):
        imported = 0
        updated = 0

        if source_path.suffix.lower() == '.zip':
            content_reader = self.build_zip_content_reader(source_path)
        else:
            content_reader = self.build_file_content_reader(source_path)

        with content_reader as reader:
            for entry in entries:
                template, created = self.upsert_template_document(reader, entry, user)
                if created:
                    imported += 1
                elif template.metadata.get('last_import_changed'):
                    updated += 1

        return imported, updated

    def build_zip_content_reader(self, source_path):
        archive = zipfile.ZipFile(source_path)

        class ZipContentReader:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc, traceback):
                archive.close()

            def read(self_inner, entry):
                with archive.open(entry['zip_info']) as zip_file:
                    return zip_file.read()

        return ZipContentReader()

    def build_file_content_reader(self, source_path):
        class FileContentReader:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc, traceback):
                return None

            def read(self_inner, entry):
                return source_path.read_bytes()

        return FileContentReader()

    def upsert_template_document(self, content_reader, entry, user):
        existing = TemplateDocument.objects.filter(
            source_path=entry['source_path']
        ).select_related('document').first()

        if existing:
            document = existing.document
            changed = existing.source_checksum != entry['source_checksum']
            if document.file and not document.file.storage.exists(document.file.name):
                changed = True
        else:
            document = Document(uploaded_by=user)
            changed = True

        if changed:
            content = content_reader.read(entry)
            document.file.save(
                entry['source_filename'],
                ContentFile(content),
                save=False,
            )

        description = f"Imported template library file: {entry['source_path']}"
        mime_type = mimetypes.guess_type(entry['source_filename'])[0] or ''
        document.title = entry['title']
        document.description = description
        document.mime_type = mime_type
        document.uploaded_by = user
        if changed:
            document.save()
        else:
            Document.objects.filter(pk=document.pk).update(
                title=entry['title'],
                description=description,
                mime_type=mime_type,
                uploaded_by=user,
            )

        metadata = {
            **entry['metadata'],
            'last_import_changed': changed,
        }
        template_values = {
            'title': entry['title'],
            'module': entry['module'],
            'document_type': entry['document_type'],
            'document_code': entry['document_code'],
            'version': entry['version'],
            'document': document,
            'framework': entry['framework'],
            'source_filename': entry['source_filename'],
            'source_checksum': entry['source_checksum'],
            'source_modified_at': entry['source_modified_at'],
            'metadata': metadata,
            'imported_by': user,
        }
        template, created = TemplateDocument.objects.update_or_create(
            source_path=entry['source_path'],
            defaults=template_values,
        )
        return template, created

    def record_import_audit_event(self, *, source_path, entries, user, imported, updated):
        log_audit_event(
            actor=user,
            event='TEMPLATE_LIBRARY_IMPORTED',
            object_type='catalogs.TemplateDocument',
            source={'type': 'import', 'reference': str(source_path)},
            details={
                'source_file': str(source_path),
                'imported_count': imported,
                'updated_count': updated,
                'skipped_count': self.skipped_count,
                'total_importable': len(entries),
                'modules': self.count_by_key(entries, 'module'),
                'document_types': self.count_by_key(entries, 'document_type'),
            },
        )

    def count_by_key(self, entries, key):
        counts: dict[str, int] = {}
        for entry in entries:
            value = entry[key]
            counts[value] = counts.get(value, 0) + 1
        return counts

    def show_dry_run_summary(self, entries):
        self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        self.stdout.write(f'Importable documents: {len(entries)}')
        self.stdout.write(f'Skipped files: {self.skipped_count}')
        self.stdout.write(f'Modules: {self.count_by_key(entries, "module")}')
        self.stdout.write(f'Document types: {self.count_by_key(entries, "document_type")}')

        self.stdout.write('\nSample documents:')
        for entry in entries[:5]:
            self.stdout.write(
                f'  - {entry["module"]}/{entry["document_type"]}: '
                f'{entry["source_filename"]}'
            )
