"""
Custom Azure Blob Storage backend with multi-tenant support.

This module provides a Django storage backend that:
1. Uses Azure Blob Storage for file storage
2. Supports tenant-specific containers for data isolation
3. Falls back to local Azurite for development
4. Handles secure file access with tenant checks
"""

import os
from django.core.files.storage import Storage, FileSystemStorage
from django.conf import settings
from django.utils.deconstruct import deconstructible
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
from django_tenants.utils import get_tenant_model, schema_context
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


@deconstructible
class TenantAwareBlobStorage(Storage):
    """
    Azure Blob Storage backend with tenant isolation.
    
    Each tenant gets their own container for complete data isolation.
    Container naming: tenant-{tenant_slug}
    """
    
    def __init__(self, connection_string=None, container_prefix="tenant"):
        self.connection_string = connection_string or os.environ.get(
            'AZURE_STORAGE_CONNECTION_STRING'
        )
        self.container_prefix = container_prefix
        self._blob_client = None
        self._fallback_storage = None
        
    @property
    def blob_client(self):
        """Lazy initialization of blob client."""
        if self._blob_client is None:
            if not self.connection_string:
                raise ValueError("Azure Storage connection string not configured")
            self._blob_client = BlobServiceClient.from_connection_string(self.connection_string)
        return self._blob_client
    
    @property 
    def fallback_storage(self):
        """Fallback to local file system storage if Azure is unavailable."""
        if self._fallback_storage is None:
            # Create tenant-aware local storage
            from django.conf import settings
            media_root = getattr(settings, 'MEDIA_ROOT', '/tmp/media')
            container_name = self._get_tenant_container_name()
            tenant_media_root = os.path.join(media_root, container_name)
            os.makedirs(tenant_media_root, exist_ok=True)
            self._fallback_storage = FileSystemStorage(location=tenant_media_root)
        return self._fallback_storage
    
    def _is_azure_available(self):
        """Check if Azure Storage is available."""
        try:
            # Simple connectivity test
            self.blob_client.get_account_information()
            return True
        except (ServiceRequestError, Exception) as e:
            logger.warning(f"Azure Storage unavailable, falling back to local storage: {e}")
            return False
        
    def _get_tenant_container_name(self):
        """Get the container name for the current tenant."""
        try:
            from django_tenants.utils import get_tenant
            tenant = get_tenant()
            if tenant and hasattr(tenant, 'slug'):
                return f"{self.container_prefix}-{tenant.slug}"
            else:
                # Fallback for shared schema or when no tenant context
                return f"{self.container_prefix}-shared"
        except Exception:
            # Fallback for non-tenant contexts (management commands, etc.)
            return f"{self.container_prefix}-shared"
    
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
    
    def _clean_name(self, name):
        """Clean the file name for Azure Blob Storage."""
        return name.replace('\\', '/')
    
    def _open(self, name, mode='rb'):
        """Open and return a file-like object."""
        name = self._clean_name(name)
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
        container_client = self._get_container_client()
        blob_client = container_client.get_blob_client(name)
        
        try:
            properties = blob_client.get_blob_properties()
            return properties.last_modified
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File '{name}' not found in tenant storage")


# Convenience storage instances are created by Django's storage system