"""
MinIO/S3 Storage Service for PhishCatcher

Handles file uploads, downloads, and management using MinIO S3-compatible storage.
"""

import io
import uuid
import mimetypes
from datetime import timedelta
from typing import Optional, BinaryIO, List, Dict, Any, Union
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from minio.helpers import ObjectWriteResult

from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class StorageService:
    """MinIO/S3 storage service for file operations."""
    
    _instance = None
    _client: Optional[Minio] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MinIO/S3 client."""
        settings = get_settings()
        config = settings.storage_config
        
        if not config:
            raise ValueError("No storage configuration found. Set MINIO_ENDPOINT or S3_ENDPOINT.")
        
        try:
            # Determine if we should use HTTPS
            secure = config.get("secure", False)
            endpoint = config["endpoint"]
            
            # Remove protocol if present in endpoint
            if endpoint.startswith("http://"):
                endpoint = endpoint[7:]
                secure = False
            elif endpoint.startswith("https://"):
                endpoint = endpoint[8:]
                secure = True
            
            self._client = Minio(
                endpoint,
                access_key=config["access_key"],
                secret_key=config["secret_key"],
                secure=secure,
                region=config.get("region", "us-east-1")
            )
            self.bucket_name = config["bucket"]
            self._ensure_bucket_exists()
            logger.info(f"Storage client initialized: {endpoint} (bucket: {self.bucket_name})")
        except Exception as e:
            logger.error(f"Failed to initialize storage client: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists with proper policies."""
        try:
            if not self._client.bucket_exists(self.bucket_name):
                self._client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
                
                # Set bucket policy for public read of specific paths (adjust as needed)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/public/*"]
                        }
                    ]
                }
                self._client.set_bucket_policy(self.bucket_name, policy)
        except S3Error as e:
            logger.error(f"S3 error ensuring bucket exists: {e}")
            raise
    
    async def upload_file(
        self,
        file_data: Union[BinaryIO, bytes],
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        folder: Optional[str] = None,
        is_public: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a file to storage.
        
        Args:
            file_data: File binary data or bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            metadata: Custom metadata to store with object
            folder: Optional folder path (e.g., "emails/2024/01")
            is_public: Whether file should be publicly accessible
        
        Returns:
            Dict with file info: object_name, url, size, etag
        """
        settings = get_settings()
        
        # Validate file extension
        ext = Path(filename).suffix.lower().lstrip('.')
        if ext not in settings.allowed_extensions_set:
            raise ValueError(f"File type .{ext} not allowed. Allowed: {settings.ALLOWED_FILE_EXTENSIONS}")
        
        # Generate unique object name
        file_id = str(uuid.uuid4())
        safe_filename = Path(filename).name.replace(" ", "_")
        
        # Build path
        base_path = "public" if is_public else "private"
        if folder:
            object_name = f"{base_path}/{folder}/{file_id}_{safe_filename}"
        else:
            object_name = f"{base_path}/{file_id}_{safe_filename}"
        
        # Auto-detect content type
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"
        
        # Prepare metadata
        meta = {
            "original-filename": filename,
            "upload-timestamp": str(uuid.uuid1().time),
            "is-public": str(is_public).lower(),
            **(metadata or {})
        }
        
        try:
            # Convert bytes to BytesIO if needed
            if isinstance(file_data, bytes):
                file_data = io.BytesIO(file_data)
            
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning
            
            if file_size > settings.max_upload_size:
                raise ValueError(f"File size {file_size} exceeds maximum {settings.max_upload_size}")
            
            # Upload to storage
            result: ObjectWriteResult = self._client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=meta
            )
            
            logger.info(f"Uploaded file: {object_name} ({file_size} bytes)")
            
            # Generate URL
            if is_public:
                url = self.get_public_url(object_name)
            else:
                url = self.get_presigned_url(object_name, expires=timedelta(days=7))
            
            return {
                "object_name": object_name,
                "bucket": self.bucket_name,
                "etag": result.etag,
                "version_id": result.version_id,
                "size": file_size,
                "content_type": content_type,
                "metadata": meta,
                "url": url,
                "is_public": is_public
            }
            
        except S3Error as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise
    
    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        folder: Optional[str] = None,
        is_public: bool = False
    ) -> Dict[str, Any]:
        """Upload bytes directly to storage."""
        return await self.upload_file(
            file_data=data,
            filename=filename,
            content_type=content_type,
            metadata=metadata,
            folder=folder,
            is_public=is_public
        )
    
    def get_file(self, object_name: str) -> bytes:
        """Download a file from storage."""
        try:
            response = self._client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Failed to get file {object_name}: {e}")
            raise
    
    def get_file_stream(self, object_name: str):
        """Get a file stream for chunked reading."""
        try:
            response = self._client.get_object(self.bucket_name, object_name)
            for chunk in response.stream(32*1024):  # 32KB chunks
                yield chunk
            response.close()
            response.release_conn()
        except S3Error as e:
            logger.error(f"Failed to stream file {object_name}: {e}")
            raise
    
    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        response_headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Generate a presigned URL for temporary access."""
        try:
            url = self._client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=expires,
                response_headers=response_headers
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            raise
    
    def get_public_url(self, object_name: str) -> str:
        """Get public URL for public objects."""
        # Build public URL based on endpoint
        settings = get_settings()
        config = settings.storage_config
        
        protocol = "https" if config.get("secure") else "http"
        endpoint = config["endpoint"].replace("http://", "").replace("https://", "")
        
        return f"{protocol}://{endpoint}/{self.bucket_name}/{object_name}"
    
    def get_presigned_upload_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(minutes=15),
        content_type: Optional[str] = None
    ) -> str:
        """Generate a presigned URL for direct browser upload."""
        try:
            conditions = []
            if content_type:
                conditions.append(["eq", "$Content-Type", content_type])
            
            policy = self._client.presigned_put_object(
                self.bucket_name,
                object_name,
                expires=expires
            )
            return policy
        except S3Error as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """Delete a file from storage."""
        try:
            self._client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted file: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            return False
    
    def list_files(
        self,
        prefix: Optional[str] = None,
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """List files in bucket with optional prefix filter."""
        try:
            objects = self._client.list_objects(
                self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            
            files = []
            for obj in objects:
                files.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "content_type": obj.content_type
                })
            
            return files
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            raise
    
    def get_file_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file without downloading."""
        try:
            stat = self._client.stat_object(self.bucket_name, object_name)
            return {
                "object_name": stat.object_name,
                "size": stat.size,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            logger.error(f"Failed to get file info for {object_name}: {e}")
            raise
    
    def copy_file(self, source_object: str, dest_object: str) -> bool:
        """Copy a file within the bucket."""
        try:
            source = f"{self.bucket_name}/{source_object}"
            self._client.copy_object(
                self.bucket_name,
                dest_object,
                source
            )
            logger.info(f"Copied {source_object} to {dest_object}")
            return True
        except S3Error as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    def move_file(self, source_object: str, dest_object: str) -> bool:
        """Move a file (copy then delete)."""
        if self.copy_file(source_object, dest_object):
            return self.delete_file(source_object)
        return False

# Singleton instance
storage_service = StorageService()