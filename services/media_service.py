import uuid
import logging
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def _get_supabase():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def validate_file(file):
    """
    Validate file type via magic bytes and size limits.
    Returns (media_type, mime_type) or raises ValidationError.
    """
    import magic

    header = file.read(2048)
    file.seek(0)

    mime = magic.from_buffer(header, mime=True)

    if mime in settings.ALLOWED_IMAGE_TYPES:
        media_type = 'image'
        max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    elif mime in settings.ALLOWED_VIDEO_TYPES:
        media_type = 'video'
        max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
    else:
        raise ValidationError(
            f'Unsupported file type: {mime}. '
            f'Allowed: JPG, PNG, WebP, MP4, MOV.'
        )

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ValidationError(
            f'File too large. Max {limit_mb}MB for {media_type}s.'
        )

    return media_type, mime


def upload_incident_media(file, incident_id):
    """
    Validate and upload file to Supabase Storage.
    Returns: {url, storage_path, media_type, file_size_kb}
    """
    media_type, mime = validate_file(file)

    ext = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/webp': 'webp',
        'video/mp4': 'mp4',
        'video/quicktime': 'mov',
    }.get(mime, 'bin')

    storage_path = f'incidents/{incident_id}/{uuid.uuid4()}.{ext}'
    file_bytes = file.read()
    file_size_kb = max(1, len(file_bytes) // 1024)

    supabase = _get_supabase()
    bucket = settings.SUPABASE_STORAGE_BUCKET

    supabase.storage.from_(bucket).upload(
        storage_path,
        file_bytes,
        {'content-type': mime},
    )

    public_url = supabase.storage.from_(bucket).get_public_url(storage_path)

    return {
        'url': public_url,
        'storage_path': storage_path,
        'media_type': media_type,
        'file_size_kb': file_size_kb,
    }


def delete_incident_media(storage_path):
    """Delete a file from Supabase Storage bucket."""
    supabase = _get_supabase()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    supabase.storage.from_(bucket).remove([storage_path])
