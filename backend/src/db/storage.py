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


def upload_base64_video(storage_client, bucket_name: str, blob_path: str, data_url: str) -> str:
    """
    Upload a base64 video data URL to GCS and return the public URL.

    Args:
        storage_client: GCS client
        bucket_name: GCS bucket name
        blob_path: path within bucket (e.g., "canvases/{canvas_id}/{node_id}.mp4")
        data_url: base64 data URL string (e.g., "data:video/mp4;base64,AAAA...")

    Returns:
        Public URL string
    """
    match = re.match(r"data:(video/[\w.+-]+);base64,(.+)", data_url, re.DOTALL)
    if not match:
        raise ValueError("Invalid video data URL format")

    content_type = match.group(1)
    video_data = base64.b64decode(match.group(2))

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(video_data, content_type=content_type)

    return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"


def get_video_extension(data_url: str) -> str:
    """Infer extension from a video data URL."""
    if data_url.startswith("data:video/webm"):
        return "webm"
    if data_url.startswith("data:video/quicktime"):
        return "mov"
    if data_url.startswith("data:video/x-msvideo"):
        return "avi"
    return "mp4"


def upload_parent_videos(parent_nodes, canvas_id: str, gcs_client, bucket_name: str):
    """
    Upload any base64 parent video nodes and replace URLs in-place with public GCS URLs.
    """
    video_nodes = [
        node for node in (parent_nodes or [])
        if node.get("type") == "videoNode"
        and is_base64_data_url(node.get("data", {}).get("videoDataUrl", ""))
    ]

    for node in video_nodes:
        video_data_url = node.get("data", {}).get("videoDataUrl", "")
        ext = get_video_extension(video_data_url)
        blob_path = f"canvases/{canvas_id}/{node['id']}.{ext}"
        try:
            public_url = upload_base64_video(
                gcs_client, bucket_name, blob_path, video_data_url
            )
            node["data"]["videoDataUrl"] = public_url
        except Exception as e:
            print(f"Error uploading parent video for node {node['id']}: {e}")


def delete_blobs(storage_client, bucket_name: str, blob_paths: list[str]):
    """
    Delete multiple blobs from GCS.

    Args:
        storage_client: GCS client
        bucket_name: GCS bucket name
        blob_paths: list of paths within bucket to delete
    """
    bucket = storage_client.bucket(bucket_name)
    for path in blob_paths:
        blob = bucket.blob(path)
        blob.delete()
