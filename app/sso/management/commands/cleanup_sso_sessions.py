"""
Management command to cleanup expired SSO sessions and audit logs.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from sso.models import SSOSession, SSOAuditLog


class Command(BaseCommand):
    help = 'Cleanup expired SSO sessions and old audit logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Keep audit logs newer than this many days (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write("DRY RUN MODE - No data will be deleted")

        # Cleanup expired sessions
        self.cleanup_expired_sessions(dry_run)

        # Cleanup old audit logs
        self.cleanup_old_audit_logs(days, dry_run)

    def cleanup_expired_sessions(self, dry_run=False):
        """Mark expired sessions as expired."""
        now = timezone.now()

        expired_sessions = SSOSession.objects.filter(
            status='active',
            expires_at__lt=now
        )

        count = expired_sessions.count()

        if count == 0:
            self.stdout.write("No expired sessions found")
            return

        if dry_run:
            self.stdout.write(f"Would mark {count} expired sessions")
        else:
            expired_sessions.update(status='expired')
            self.stdout.write(
                self.style.SUCCESS(f"Marked {count} expired sessions")
            )

    def cleanup_old_audit_logs(self, days, dry_run=False):
        """Delete old audit logs."""
        cutoff_date = timezone.now() - timedelta(days=days)

        old_logs = SSOAuditLog.objects.filter(
            event_timestamp__lt=cutoff_date
        )

        count = old_logs.count()

        if count == 0:
            self.stdout.write(f"No audit logs older than {days} days found")
            return

        if dry_run:
            self.stdout.write(f"Would delete {count} audit logs older than {days} days")
        else:
            old_logs.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {count} audit logs older than {days} days"
                )
            )