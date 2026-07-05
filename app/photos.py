from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import get_settings


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class PhotoValidationError(ValueError):
    pass


async def save_photo(upload: UploadFile | None, old_photo_path: str | None = None) -> str | None:
    if not upload or not upload.filename:
        return None

    settings = get_settings()
    extension = Path(upload.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise PhotoValidationError("Фото должно быть файлом JPG, PNG, WEBP или GIF")

    content = await upload.read()
    if len(content) > settings.max_photo_size_bytes:
        raise PhotoValidationError("Размер фото не должен превышать 200 КБ")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    target = settings.upload_dir / filename
    target.write_bytes(content)

    if old_photo_path:
        delete_photo(old_photo_path)

    return f"/uploads/{filename}"


def delete_photo(photo_path: str | None) -> None:
    if not photo_path:
        return
    settings = get_settings()
    filename = Path(photo_path).name
    target = settings.upload_dir / filename
    if target.exists() and target.is_file():
        target.unlink()

