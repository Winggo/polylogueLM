import base64
import re
from google.cloud import storage


def start_storage_client(project: str):
    """Initialize and return a GCS client."""
    return storage.Client(project=project)


def is_base64_data_url(value: str) -> bool:
    """Check if a string is a base64 data URL (not already a GCS/HTTP URL)."""
    return isinstance(value, str) and value.startswith("data:")


def upload_base64_image(storage_client, bucket_name: str, blob_path: str, data_url: str) -> str:
    """
    Upload a base64 data URL to GCS and return the public URL.

    Args:
        storage_client: GCS client
        bucket_name: GCS bucket name
        blob_path: path within bucket (e.g., "canvases/{canvas_id}/{node_id}.png")
        data_url: base64 data URL string (e.g., "data:image/png;base64,iVBOR...")

    Returns:
        Public URL string
    """
    match = re.match(r"data:(image/\w+);base64,(.+)", data_url, re.DOTALL)
    if not match:
        raise ValueError("Invalid data URL format")

    content_type = match.group(1)
    image_data = base64.b64decode(match.group(2))

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(image_data, content_type=content_type)

    return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
