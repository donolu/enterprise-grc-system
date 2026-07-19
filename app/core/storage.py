"""
Tenant-aware storage backends with multi-provider support.

This module provides a Django storage backend that:
1. Uses tenant-specific Azure containers, S3-compatible prefixes, or local paths.
2. Preserves tenant isolation regardless of the configured provider.
3. Falls back to local storage for Azure development when configured storage is unavailable.
4. Handles secure file access with tenant checks in the application layer.
"""

import logging
import os
from urllib.parse import quote, urljoin

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.db import connection
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
except ModuleNotFoundError:
    BlobServiceClient = None

    class ResourceNotFoundError(Exception):
        pass

    class ServiceRequestError(Exception):
        pass


class TenantStorageMixin:
    """Shared tenant naming helpers for storage backends."""

    container_prefix = "tenant"

    def _clean_name(self, name):
        return str(name).replace("\\", "/").lstrip("/")

    def _get_tenant_container_name(self):
        """Get the storage namespace for the current tenant."""
        tenant = getattr(connection, "tenant", None)
        if tenant and getattr(tenant, "slug", None):
            return f"{self.container_prefix}-{tenant.slug}"

        # Fallback for shared schema or non-tenant contexts.
        return f"{self.container_prefix}-shared"

    def _tenant_key(self, name):
        return f"{self._get_tenant_container_name()}/{self._clean_name(name)}"

    def storage_backend_name(self):
        return self.__class__.__name__

    def storage_health(self):
        return {
            "status": "healthy",
            "message": f"{self.storage_backend_name()} configured",
        }


@deconstructible
class TenantAwareFileSystemStorage(TenantStorageMixin, FileSystemStorage):
    """Tenant-aware local filesystem storage for self-hosted and test deployments."""

    def __init__(self, location=None, base_url=None, container_prefix=None):
        self.container_prefix = container_prefix or getattr(
            settings,
            "TENANT_STORAGE_PREFIX",
            "tenant",
        )
        super().__init__(
            location=location or getattr(settings, "MEDIA_ROOT", "/tmp/media"),
            base_url=base_url or getattr(settings, "MEDIA_URL", "/media/"),
        )

    def _open(self, name, mode="rb"):
        return super()._open(self._tenant_key(name), mode)

    def _save(self, name, content):
        saved_name = super()._save(self._tenant_key(name), content)
        prefix = f"{self._get_tenant_container_name()}/"
        if saved_name.startswith(prefix):
            return saved_name[len(prefix):]
        return saved_name

    def delete(self, name):
        return super().delete(self._tenant_key(name))

    def exists(self, name):
        return super().exists(self._tenant_key(name))

    def listdir(self, path):
        return super().listdir(self._tenant_key(path))

    def size(self, name):
        return super().size(self._tenant_key(name))

    def url(self, name):
        return super().url(self._tenant_key(name))

    def get_accessed_time(self, name):
        return super().get_accessed_time(self._tenant_key(name))

    def get_created_time(self, name):
        return super().get_created_time(self._tenant_key(name))

    def get_modified_time(self, name):
        return super().get_modified_time(self._tenant_key(name))


@deconstructible
class TenantAwareS3Storage(TenantStorageMixin, Storage):
    """
    S3-compatible tenant-aware object storage.

    The backend uses one bucket and stores each tenant under its own key prefix,
    which works across AWS S3, DigitalOcean Spaces, Cloudflare R2, MinIO, and
    other S3-compatible providers.
    """

    def __init__(
        self,
        bucket_name=None,
        endpoint_url=None,
        region_name=None,
        access_key_id=None,
        secret_access_key=None,
        public_base_url=None,
        addressing_style=None,
        container_prefix=None,
        create_bucket=None,
    ):
        self.bucket_name = (
            bucket_name
            or getattr(settings, "OBJECT_STORAGE_BUCKET", None)
            or os.environ.get("OBJECT_STORAGE_BUCKET")
            or os.environ.get("AWS_STORAGE_BUCKET_NAME")
        )
        self.endpoint_url = (
            endpoint_url
            or getattr(settings, "OBJECT_STORAGE_ENDPOINT_URL", None)
            or os.environ.get("OBJECT_STORAGE_ENDPOINT_URL")
            or os.environ.get("AWS_S3_ENDPOINT_URL")
        )
        self.region_name = (
            region_name
            or getattr(settings, "OBJECT_STORAGE_REGION", None)
            or os.environ.get("OBJECT_STORAGE_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "eu-west-2"
        )
        self.access_key_id = (
            access_key_id
            or getattr(settings, "OBJECT_STORAGE_ACCESS_KEY_ID", None)
            or os.environ.get("OBJECT_STORAGE_ACCESS_KEY_ID")
            or os.environ.get("AWS_ACCESS_KEY_ID")
        )
        self.secret_access_key = (
            secret_access_key
            or getattr(settings, "OBJECT_STORAGE_SECRET_ACCESS_KEY", None)
            or os.environ.get("OBJECT_STORAGE_SECRET_ACCESS_KEY")
            or os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        self.public_base_url = (
            public_base_url
            or getattr(settings, "OBJECT_STORAGE_PUBLIC_BASE_URL", "")
            or os.environ.get("OBJECT_STORAGE_PUBLIC_BASE_URL", "")
        )
        self.addressing_style = (
            addressing_style
            or getattr(settings, "OBJECT_STORAGE_ADDRESSING_STYLE", "auto")
            or "auto"
        )
        self.container_prefix = container_prefix or getattr(
            settings,
            "TENANT_STORAGE_PREFIX",
            "tenant",
        )
        self.create_bucket = (
            create_bucket
            if create_bucket is not None
            else getattr(settings, "OBJECT_STORAGE_CREATE_BUCKET", False)
        )
        self._client = None

    @property
    def client(self):
        if self._client is None:
            client_kwargs = {
                "service_name": "s3",
                "region_name": self.region_name,
                "endpoint_url": self.endpoint_url,
                "aws_access_key_id": self.access_key_id,
                "aws_secret_access_key": self.secret_access_key,
            }
            if self.addressing_style and self.addressing_style != "auto":
                client_kwargs["config"] = Config(
                    s3={"addressing_style": self.addressing_style},
                )
            self._client = boto3.client(**client_kwargs)
        return self._client

    def _require_bucket(self):
        if not self.bucket_name:
            raise ValueError("OBJECT_STORAGE_BUCKET or AWS_STORAGE_BUCKET_NAME is required")

    def _ensure_bucket(self):
        self._require_bucket()
        if not self.create_bucket:
            return
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket_name)

    def _open(self, name, mode="rb"):
        self._require_bucket()
        key = self._tenant_key(name)
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                raise FileNotFoundError(f"File '{name}' not found in tenant storage")
            raise
        return ContentFile(response["Body"].read(), name=name)

    def _save(self, name, content):
        self._ensure_bucket()
        key = self._tenant_key(name)
        if hasattr(content, "seek"):
            content.seek(0)
        self.client.upload_fileobj(content, self.bucket_name, key)
        return self._clean_name(name)

    def delete(self, name):
        self._require_bucket()
        self.client.delete_object(Bucket=self.bucket_name, Key=self._tenant_key(name))

    def exists(self, name):
        self._require_bucket()
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=self._tenant_key(name))
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                return False
            raise

    def listdir(self, path):
        self._require_bucket()
        prefix = self._tenant_key(path)
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix,
            Delimiter="/",
        )
        directories = [
            item["Prefix"][len(prefix):].rstrip("/")
            for item in response.get("CommonPrefixes", [])
        ]
        files = [
            item["Key"][len(prefix):]
            for item in response.get("Contents", [])
            if item["Key"] != prefix and "/" not in item["Key"][len(prefix):]
        ]
        return directories, files

    def size(self, name):
        self._require_bucket()
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=self._tenant_key(name))
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                raise FileNotFoundError(f"File '{name}' not found in tenant storage")
            raise
        return response["ContentLength"]

    def url(self, name):
        self._require_bucket()
        key = self._tenant_key(name)
        if self.public_base_url:
            return urljoin(self.public_base_url.rstrip("/") + "/", quote(key))
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
        )

    def get_accessed_time(self, name):
        raise NotImplementedError("Object storage does not provide access time")

    def get_created_time(self, name):
        raise NotImplementedError("Object storage does not provide creation time")

    def get_modified_time(self, name):
        self._require_bucket()
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=self._tenant_key(name))
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                raise FileNotFoundError(f"File '{name}' not found in tenant storage")
            raise
        return response["LastModified"]

    def storage_health(self):
        try:
            self._require_bucket()
            self.client.head_bucket(Bucket=self.bucket_name)
            return {"status": "healthy", "message": "S3-compatible object storage is available"}
        except (BotoCoreError, ClientError, ValueError) as exc:
            return {"status": "degraded", "message": f"Object storage unavailable: {exc}"}


@deconstructible
class TenantAwareBlobStorage(TenantStorageMixin, Storage):
    """
    Azure Blob Storage backend with tenant isolation.
    
    Each tenant gets their own container for complete data isolation.
    Container naming: tenant-{tenant_slug}
    """
    
    def __init__(self, connection_string=None, container_prefix=None):
        self.connection_string = connection_string or os.environ.get(
            'AZURE_STORAGE_CONNECTION_STRING'
        )
        self.container_prefix = container_prefix or getattr(
            settings,
            "TENANT_STORAGE_PREFIX",
            "tenant",
        )
        self._blob_client = None
        self._fallback_storages = {}
        
    @property
    def blob_client(self):
        """Lazy initialization of blob client."""
        if self._blob_client is None:
            if not self.connection_string:
                raise ValueError("Azure Storage connection string not configured")
            if BlobServiceClient is None:
                raise ValueError("azure-storage-blob is required for STORAGE_BACKEND=azure")
            self._blob_client = BlobServiceClient.from_connection_string(self.connection_string)
        return self._blob_client
    
    @property 
    def fallback_storage(self):
        """Fallback to local file system storage if Azure is unavailable."""
        container_name = self._get_tenant_container_name()
        if container_name not in self._fallback_storages:
            # Create tenant-aware local storage
            from django.conf import settings
            media_root = getattr(settings, 'MEDIA_ROOT', '/tmp/media')
            tenant_media_root = os.path.join(media_root, container_name)
            os.makedirs(tenant_media_root, exist_ok=True)
            self._fallback_storages[container_name] = FileSystemStorage(
                location=tenant_media_root
            )
        return self._fallback_storages[container_name]
    
    def _is_azure_available(self):
        """Check if Azure Storage is available."""
        try:
            # Simple connectivity test
            self.blob_client.get_account_information()
            return True
        except (ServiceRequestError, Exception) as e:
            logger.warning(f"Azure Storage unavailable, falling back to local storage: {e}")
            return False
        
    def _get_container_client(self, container_name=None):
        """Get a container client for the specified or current tenant."""
        if container_name is None:
            container_name = self._get_tenant_container_name()
        
        container_client = self.blob_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.get_container_properties()
        except ResourceNotFoundError:
            container_client.create_container()
            
        return container_client
    
    def _open(self, name, mode='rb'):
        """Open and return a file-like object."""
        name = self._clean_name(name)
        if not self._is_azure_available():
            return self.fallback_storage._open(name, mode)

        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(name)
        
        try:
            blob_data = blob_client.download_blob()
            return blob_data.readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File '{name}' not found in tenant storage")
    
    def _save(self, name, content):
        """Save the file content to Azure Blob Storage or fallback to local storage."""
        name = self._clean_name(name)
        
        # Try Azure Storage first
        if self._is_azure_available():
            try:
                container_client = self._get_container_client()
                blob_client = container_client.get_blob_client(name)
                blob_client.upload_blob(content, overwrite=True)
                logger.info(f"File saved to Azure Storage: {name}")
                return name
            except Exception as e:
                logger.warning(f"Failed to save to Azure Storage: {e}, falling back to local storage")
        
        # Fallback to local storage
        logger.info(f"Saving file to local storage: {name}")
        return self.fallback_storage._save(name, content)
    
    def delete(self, name):
        """Delete the specified file."""
        name = self._clean_name(name)
        if not self._is_azure_available():
            return self.fallback_storage.delete(name)

        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(name)
        
        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass  # File already doesn't exist
    
    def exists(self, name):
        """Check if a file exists."""
        name = self._clean_name(name)
        
        # Try Azure Storage first
        if self._is_azure_available():
            try:
                container_client = self._get_container_client()
                blob_client = container_client.get_blob_client(name)
                blob_client.get_blob_properties()
                return True
            except ResourceNotFoundError:
                return False
            except Exception:
                pass  # Fall through to local storage check
        
        # Check local storage
        return self.fallback_storage.exists(name)
    
    def listdir(self, path):
        """List the contents of the specified path."""
        path = self._clean_name(path)
        if not self._is_azure_available():
            return self.fallback_storage.listdir(path)

        container_client = self._get_container_client()
        
        if path and not path.endswith('/'):
            path += '/'
        
        directories = set()
        files = []
        
        for blob in container_client.list_blobs(name_starts_with=path):
            blob_name = blob.name
            if path:
                blob_name = blob_name[len(path):]
            
            if '/' in blob_name:
                # This is in a subdirectory
                dir_name = blob_name.split('/')[0]
                directories.add(dir_name)
            else:
                # This is a file in the current directory
                files.append(blob_name)
        
        return list(directories), files
    
    def size(self, name):
        """Return the size of the specified file."""
        name = self._clean_name(name)
        if not self._is_azure_available():
            return self.fallback_storage.size(name)

        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(name)
        
        try:
            properties = blob_client.get_blob_properties()
            return properties.size
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File '{name}' not found in tenant storage")
    
    def url(self, name):
        """Return the URL for the specified file."""
        name = self._clean_name(name)
        
        # Try Azure Storage first
        if self._is_azure_available():
            container_name = self._get_tenant_container_name()
            
            # For development with Azurite
            if 'devstoreaccount1' in self.connection_string:
                return f"http://localhost:10000/devstoreaccount1/{container_name}/{name}"
            
            # For production Azure Storage
            account_name = self._extract_account_name()
            return f"https://{account_name}.blob.core.windows.net/{container_name}/{name}"
        
        # Fallback to local storage URL
        return self.fallback_storage.url(name)
    
    def _extract_account_name(self):
        """Extract the storage account name from connection string."""
        # Parse connection string for AccountName
        for part in self.connection_string.split(';'):
            if part.startswith('AccountName='):
                return part.split('=', 1)[1]
        return 'unknown'
    
    def get_accessed_time(self, name):
        """Azure Blob Storage doesn't track access time."""
        raise NotImplementedError("Azure Blob Storage doesn't provide access time")
    
    def get_created_time(self, name):
        """Return the creation time of the specified file."""
        name = self._clean_name(name)
        if not self._is_azure_available():
            return self.fallback_storage.get_created_time(name)

        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(name)
        
        try:
            properties = blob_client.get_blob_properties()
            return properties.creation_time
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File '{name}' not found in tenant storage")
    
    def get_modified_time(self, name):
        """Return the modification time of the specified file."""
        name = self._clean_name(name)
        if not self._is_azure_available():
            return self.fallback_storage.get_modified_time(name)

        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(name)
        
        try:
            properties = blob_client.get_blob_properties()
            return properties.last_modified
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File '{name}' not found in tenant storage")

    def storage_health(self):
        if self._is_azure_available():
            return {"status": "healthy", "message": "Azure Blob Storage is available"}
        return {"status": "degraded", "message": "Azure Blob Storage unavailable, using fallback"}


# Convenience storage instances are created by Django's storage system
