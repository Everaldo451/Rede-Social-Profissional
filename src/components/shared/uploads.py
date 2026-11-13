from services.shared.media_service import ALLOWED_TYPES, MediaFile


def to_media_files(uploaded_files) -> list[MediaFile]:
    return [
        MediaFile(f.name, f.type or "application/octet-stream", f.getvalue())
        for f in (uploaded_files or [])
    ]


UPLOAD_TYPES = ["png", "jpg", "jpeg", "gif", "webp", "mp4", "webm", "pdf"]
UPLOAD_HELP = "Imagens, vídeos (MP4/WEBM) ou PDF — até 4 arquivos de 10 MB."
