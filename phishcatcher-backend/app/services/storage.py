"""
MinIO Storage Service for PhishCatcher

Handles file uploads, downloads, and management using MinIO object storage.
"""

import io
import uuid
import mimetypes
from datetime import timedelta
from typing import Optional, BinaryIO, List, Dict, Any, Union
from pathlib import Path

from minio import Minio
from minio.error import MinioException
from minio.helpers import ObjectWriteResult
from urllib.parse import urlparse

from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class StorageService:
    """MinIO storage service for file operations."""
    
    _instance = None
    _client: Optional[Minio] = None
    _initialized = False
    _available = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            try:
                self._initialize_client()
                self._available = True
                logger.info("MinIO storage service initialized successfully")
            except Exception as e:
                logger.warning(f"MinIO storage service unavailable: {e}")
                self._available = False
    
    @property
    def is_available(self) -> bool:
        """Check if MinIO storage is available."""
        return self._available and self._client is not None
    
    def _initialize_client(self):
        """Initialize MinIO client."""
        settings = get_settings()
        
        # Get MinIO configuration
        endpoint = settings.MINIO_ENDPOINT
        access_key = settings.MINIO_ACCESS_KEY
        secret_key = settings.MINIO_SECRET_KEY
        secure = settings.MINIO_SECURE
        region = settings.MINIO_REGION
        
        if not all([endpoint, access_key, secret_key]):
            raise ValueError("Incomplete MinIO configuration. Set MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY")
        
        # Build endpoint candidates:
        # - configured endpoint (e.g. minio:9000 in Docker)
        # - localhost fallback for host-run backend
        endpoint_candidates = []
        raw_endpoint = endpoint
        if raw_endpoint.startswith("http://") or raw_endpoint.startswith("https://"):
            parsed = urlparse(raw_endpoint)
            host = parsed.hostname or ""
            port = parsed.port or 9000
            endpoint_candidates.append((f"{host}:{port}", parsed.scheme == "https"))
        else:
            endpoint_candidates.append((raw_endpoint, secure))
            host_port = raw_endpoint.split(":")
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "9000"
            if host in {"minio", "minio.local"}:
                endpoint_candidates.append((f"localhost:{port}", False))

        last_error = None
        for candidate, candidate_secure in endpoint_candidates:
            try:
                client = Minio(
                    candidate,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=candidate_secure,
                    region=region
                )
                # Force connectivity test early so failures are explicit.
                client.list_buckets()
                self._client = client
                logger.info(f"MinIO client initialized: {candidate} (secure={candidate_secure})")
                return
            except Exception as e:
                last_error = e
                logger.warning(f"MinIO endpoint failed ({candidate}): {e}")

        logger.error(f"Failed to initialize MinIO client: {last_error}")
        raise last_error
    
    def _ensure_bucket_exists(self, bucket_name: str):
        """Ensure a bucket exists (private by default)."""
        try:
            if not self._client.bucket_exists(bucket_name):
                self._client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
        except MinioException as e:
            logger.error(f"MinIO error ensuring bucket exists: {e}")
            raise

    def _get_bucket(self, bucket: Optional[str]) -> str:
        settings = get_settings()
        if bucket:
            return bucket
        # Back-compat default: treat uploads as "emails" bucket.
        return settings.MINIO_BUCKET_EMAILS
    
    async def upload_file(
        self,
        file_data: Union[BinaryIO, bytes],
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        folder: Optional[str] = None,
        is_public: bool = False,
        bucket: Optional[str] = None
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
        if not self.is_available:
            raise RuntimeError("MinIO storage service is not available")
        
        settings = get_settings()
        
        ext = Path(filename).suffix.lower().lstrip('.') if filename else ''
        if not ext:
            raise ValueError("File must have an extension (e.g., .png, .jpg)")
        if ext not in settings.allowed_extensions_set:
            raise ValueError(f"File type .{ext} not allowed. Allowed: {settings.ALLOWED_FILE_EXTENSIONS}")
        
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lower()
        
        # Build path - use only UUID + extension, no original filename
        base_path = "public" if is_public else "private"
        if folder:
            object_name = f"{base_path}/{folder}/{file_id}{ext}"
        else:
            object_name = f"{base_path}/{file_id}{ext}"
        
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
        
        target_bucket = self._get_bucket(bucket)
        self._ensure_bucket_exists(target_bucket)

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
                bucket_name=target_bucket,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=meta
            )
            
            logger.info(f"Uploaded file: {object_name} ({file_size} bytes)")
            
            # Generate URL
            if is_public:
                url = self.get_public_url(object_name, bucket=target_bucket)
            else:
                url = self.get_presigned_url(object_name, expires=timedelta(days=7), bucket=target_bucket)
            
            return {
                "object_name": object_name,
                "bucket": target_bucket,
                "etag": result.etag,
                "version_id": result.version_id,
                "size": file_size,
                "content_type": content_type,
                "metadata": meta,
                "url": url,
                "is_public": is_public
            }
            
        except MinioException as e:
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
        is_public: bool = False,
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload bytes directly to storage."""
        return await self.upload_file(
            file_data=data,
            filename=filename,
            content_type=content_type,
            metadata=metadata,
            folder=folder,
            is_public=is_public,
            bucket=bucket
        )
    
    def get_file(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        """Download a file from storage."""
        target_bucket = self._get_bucket(bucket)
        try:
            response = self._client.get_object(target_bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except MinioException as e:
            logger.error(f"Failed to get file {object_name}: {e}")
            raise

    async def get_file_bytes(self, object_name: str, bucket: Optional[str] = None) -> bytes:
        """Async wrapper for get_file."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_file, object_name, bucket)
    
    def get_file_stream(self, object_name: str, bucket: Optional[str] = None):
        """Get a file stream for chunked reading."""
        target_bucket = self._get_bucket(bucket)
        try:
            response = self._client.get_object(target_bucket, object_name)
            for chunk in response.stream(32*1024):  # 32KB chunks
                yield chunk
            response.close()
            response.release_conn()
        except MinioException as e:
            logger.error(f"Failed to stream file {object_name}: {e}")
            raise
    
    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        response_headers: Optional[Dict[str, str]] = None,
        bucket: Optional[str] = None
    ) -> str:
        """Generate a presigned URL for temporary access."""
        target_bucket = self._get_bucket(bucket)
        settings = get_settings()
        try:
            url = self._client.presigned_get_object(
                target_bucket,
                object_name,
                expires=expires,
                response_headers=response_headers
            )
            
            if settings.MINIO_EXTERNAL_URL:
                internal_url = f"http://{settings.MINIO_ENDPOINT}" if not settings.MINIO_SECURE else f"https://{settings.MINIO_ENDPOINT}"
                if not internal_url.startswith("http"):
                    internal_url = f"http://{internal_url}"
                url = url.replace(internal_url, settings.MINIO_EXTERNAL_URL)
            
            return url
        except MinioException as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            raise
    
    def get_public_url(self, object_name: str, bucket: Optional[str] = None) -> str:
        """Get public URL for public objects."""
        target_bucket = self._get_bucket(bucket)
        # Build public URL based on endpoint
        settings = get_settings()
        endpoint = settings.MINIO_ENDPOINT
        secure = settings.MINIO_SECURE
        
        protocol = "https" if secure else "http"
        
        # Remove protocol if present in endpoint
        if endpoint.startswith("http://"):
            endpoint = endpoint[7:]
        elif endpoint.startswith("https://"):
            endpoint = endpoint[8:]
        
        return f"{protocol}://{endpoint}/{target_bucket}/{object_name}"
    
    def get_presigned_upload_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(minutes=15),
        content_type: Optional[str] = None,
        bucket: Optional[str] = None
    ) -> str:
        """Generate a presigned URL for direct browser upload."""
        target_bucket = self._get_bucket(bucket)
        try:
            conditions = []
            if content_type:
                conditions.append(["eq", "$Content-Type", content_type])
            
            policy = self._client.presigned_put_object(
                target_bucket,
                object_name,
                expires=expires
            )
            return policy
        except MinioException as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            raise
    
    def delete_file(self, object_name: str, bucket: Optional[str] = None) -> bool:
        """Delete a file from storage."""
        target_bucket = self._get_bucket(bucket)
        try:
            self._client.remove_object(target_bucket, object_name)
            logger.info(f"Deleted file: {object_name}")
            return True
        except MinioException as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            return False
    
    def list_files(
        self,
        prefix: Optional[str] = None,
        recursive: bool = True,
        bucket: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files in bucket with optional prefix filter."""
        target_bucket = self._get_bucket(bucket)
        try:
            objects = self._client.list_objects(
                target_bucket,
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
        except MinioException as e:
            logger.error(f"Failed to list files: {e}")
            raise
    
    def get_file_info(self, object_name: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get metadata for a file without downloading."""
        target_bucket = self._get_bucket(bucket)
        try:
            stat = self._client.stat_object(target_bucket, object_name)
            return {
                "object_name": stat.object_name,
                "size": stat.size,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
        except MinioException as e:
            # Check if it's a "not found" error
            if hasattr(e, 'code') and e.code == "NoSuchKey":
                return None
            elif "NoSuchKey" in str(e):
                return None
            logger.error(f"Failed to get file info for {object_name}: {e}")
            raise
    
    def copy_file(self, source_object: str, dest_object: str, bucket: Optional[str] = None) -> bool:
        """Copy a file within the bucket."""
        target_bucket = self._get_bucket(bucket)
        try:
            source = f"{target_bucket}/{source_object}"
            self._client.copy_object(
                target_bucket,
                dest_object,
                source
            )
            logger.info(f"Copied {source_object} to {dest_object}")
            return True
        except MinioException as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    def move_file(self, source_object: str, dest_object: str, bucket: Optional[str] = None) -> bool:
        """Move a file (copy then delete)."""
        if self.copy_file(source_object, dest_object, bucket=bucket):
            return self.delete_file(source_object, bucket=bucket)
        return False

# Singleton instance
storage_service = StorageService()