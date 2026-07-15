import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile


class DocumentConversionError(RuntimeError):
    pass


def finalize_policy_version_pdf(version):
    if not version.document:
        raise DocumentConversionError('No source document is available for finalisation.')

    extension = version.file_extension
    if extension == '.pdf':
        version.document.open('rb')
        try:
            pdf_content = version.document.read()
        finally:
            version.document.close()
        filename = f'{version.policy.policy_code}_v{version.version_number}_final.pdf'
        version.final_pdf.save(filename, ContentFile(pdf_content), save=False)
        return version.final_pdf

    if extension not in {'.doc', '.docx'}:
        raise DocumentConversionError('Only PDF, DOC and DOCX sources can be finalised.')

    if not bool(int(os.environ.get('POLICY_ENABLE_OFFICE_CONVERSION', '0'))):
        raise DocumentConversionError('Office to PDF conversion is not enabled.')

    binary = getattr(settings, 'LIBREOFFICE_BINARY', os.environ.get('LIBREOFFICE_BINARY', 'libreoffice'))
    if not shutil.which(binary):
        raise DocumentConversionError('LibreOffice binary is not available.')

    timeout = int(os.environ.get('POLICY_CONVERSION_TIMEOUT_SECONDS', '120'))
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_path = temp_path / f'source{extension}'
        version.document.open('rb')
        try:
            source_path.write_bytes(version.document.read())
        finally:
            version.document.close()

        completed = subprocess.run(  # noqa: S603
            [
                binary,
                '--headless',
                '--convert-to',
                'pdf',
                '--outdir',
                str(temp_path),
                str(source_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise DocumentConversionError(completed.stderr.strip() or 'Office conversion failed.')

        pdf_path = source_path.with_suffix('.pdf')
        if not pdf_path.exists():
            raise DocumentConversionError('Office conversion did not produce a PDF.')

        filename = f'{version.policy.policy_code}_v{version.version_number}_final.pdf'
        version.final_pdf.save(filename, ContentFile(pdf_path.read_bytes()), save=False)
        return version.final_pdf
