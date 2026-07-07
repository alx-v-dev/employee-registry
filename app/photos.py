from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import get_settings


CHUNK_SIZE = 64 * 1024
PHOTO_TYPES_BY_EXTENSION = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".webp": "webp",
    ".gif": "gif",
}


class PhotoValidationError(ValueError):
    pass


def detect_photo_type(content: bytes) -> str | None:
    """Detect the supported image type from a small set of magic byte signatures."""
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    return None


async def read_limited_upload(upload: UploadFile, max_size: int) -> bytes:
    """Read an uploaded file in chunks and fail as soon as it exceeds max_size."""
    chunks: list[bytes] = []
    total_size = 0

    while chunk := await upload.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > max_size:
            raise PhotoValidationError("Размер фото не должен превышать 200 КБ")
        chunks.append(chunk)

    return b"".join(chunks)


async def save_photo(upload: UploadFile | None) -> str | None:
    """Validate and persist a new photo, leaving rollback cleanup to the caller."""
    if not upload or not upload.filename:
        return None

    settings = get_settings()
    extension = Path(upload.filename).suffix.lower()
    expected_photo_type = PHOTO_TYPES_BY_EXTENSION.get(extension)
    if expected_photo_type is None:
        raise PhotoValidationError("Фото должно быть файлом JPG, PNG, WEBP или GIF")

    content = await read_limited_upload(upload, settings.max_photo_size_bytes)
    detected_photo_type = detect_photo_type(content)
    if detected_photo_type != expected_photo_type:
        raise PhotoValidationError("Фото должно быть файлом JPG, PNG, WEBP или GIF")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    target = settings.upload_dir / filename
    target.write_bytes(content)

    return f"/uploads/{filename}"


def delete_photo(photo_path: str | None) -> None:
    if not photo_path:
        return
    settings = get_settings()
    filename = Path(photo_path).name
    target = settings.upload_dir / filename
    if target.exists() and target.is_file():
        target.unlink()
