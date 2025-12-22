"""
MinIO service - upload and retrieve skeleton videos from object storage.

This service abstracts away direct MinIO access so the rest of the codebase
can remain clean. It is optional and controlled by MINIO_CONFIG in config.py.
"""

from functools import lru_cache
from typing import Optional, IO

from minio import Minio
from minio.error import S3Error

from backend.app.config import MINIO_CONFIG


@lru_cache()
def get_minio_client() -> Minio:
    """
    Lazily create a MinIO client based on MINIO_CONFIG.

    Returns:
        Minio client instance.
    """
    endpoint = MINIO_CONFIG.get("endpoint", "http://minio:9000")
    # Minio SDK expects bare host:port without scheme
    endpoint = endpoint.replace("http://", "").replace("https://", "")

    access_key = MINIO_CONFIG.get("access_key")
    secret_key = MINIO_CONFIG.get("secret_key")
    secure = MINIO_CONFIG.get("secure", False)

    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket_exists(bucket: str) -> None:
    """
    Ensure that the target bucket exists, create it if needed.
    """
    client = get_minio_client()
    found = client.bucket_exists(bucket)
    if not found:
        client.make_bucket(bucket)


def upload_file_to_minio(local_path: str, object_name: str) -> str:
    """
    Upload a local file to MinIO.

    Args:
        local_path: Local filesystem path to the file.
        object_name: Object name/key inside the bucket (e.g. "session_01/skeleton_video_web.mp4").

    Returns:
        The object name that was uploaded (for storage in DB).
    """
    if not MINIO_CONFIG.get("enabled", False):
        # MinIO disabled, just return object_name for consistency (caller can ignore)
        return object_name

    bucket = MINIO_CONFIG.get("bucket", "skeleton-videos")
    client = get_minio_client()

    ensure_bucket_exists(bucket)
    client.fput_object(bucket, object_name, local_path)

    return object_name


def get_object_from_minio(object_name: str) -> Optional[IO[bytes]]:
    """
    Retrieve an object stream from MinIO.

    Args:
        object_name: Object name/key inside the bucket.

    Returns:
        A streaming object handle, or None if MinIO disabled or object not found.
    """
    if not MINIO_CONFIG.get("enabled", False):
        return None

    bucket = MINIO_CONFIG.get("bucket", "skeleton-videos")
    client = get_minio_client()

    try:
        return client.get_object(bucket, object_name)
    except S3Error:
        return None


