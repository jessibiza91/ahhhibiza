import io
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image

IMAGE_FORMAT_TO_EXTENSIONS = {
    'JPEG': {'.jpg', '.jpeg', '.jpe'},
    'PNG': {'.png'},
    'WEBP': {'.webp'},
    'GIF': {'.gif'},
}

ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm'}

IGNORED_CONTENT_TYPES = {
    '',
    'application/octet-stream',
    'binary/octet-stream',
}

EBML_MAGIC = b'\x1a\x45\xdf\xa3'
QUICKTIME_BRAND = b'qt  '


def _normalized_extension(filename):
    if not filename:
        return ''
    return Path(str(filename).lower()).suffix


def _detect_image(f):
    f.seek(0)
    try:
        with Image.open(io.BytesIO(f.read())) as img:
            img.verify()
            return img.format
    except (Image.DecompressionBombError, OSError, ValueError):
        return None
    finally:
        f.seek(0)


def _detect_video(f):
    f.seek(0)
    try:
        header = f.read(16)
    finally:
        f.seek(0)

    if len(header) >= 4 and header[:4] == EBML_MAGIC:
        return 'webm'
    if len(header) >= 12 and header[4:8] == b'ftyp':
        return 'mov' if header[8:12] == QUICKTIME_BRAND else 'mp4'
    return None


def validate_uploaded_file(f):
    """Valida un archivo subido por su contenido real (magic bytes).

    Devuelve 'image' o 'video' segun el tipo detectado y lanza
    ValidationError si el archivo no es una imagen o video permitido
    (jpg/png/webp/gif, o mp4/mov/webm).
    """
    if f is None:
        return 'image'

    ext = _normalized_extension(getattr(f, 'name', ''))
    content_type = (getattr(f, 'content_type', '') or '').strip().lower()

    image_format = _detect_image(f)
    video_kind = _detect_video(f)

    if image_format and video_kind:
        raise ValidationError('El archivo no se puede clasificar de forma inequivoca.')

    if image_format:
        allowed_exts = IMAGE_FORMAT_TO_EXTENSIONS.get(image_format)
        if allowed_exts is None:
            raise ValidationError(f'El formato de imagen {image_format} no esta permitido.')
        if ext and ext not in allowed_exts:
            raise ValidationError('La extension del archivo no coincide con su contenido real (imagen).')
        if content_type and content_type not in IGNORED_CONTENT_TYPES and not content_type.startswith('image/'):
            raise ValidationError('El tipo MIME declarado no corresponde a una imagen permitida.')
        return 'image'

    if video_kind:
        if ext and ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValidationError('La extension del archivo no coincide con su contenido real (video).')
        if content_type and content_type not in IGNORED_CONTENT_TYPES and not content_type.startswith('video/'):
            raise ValidationError('El tipo MIME declarado no corresponde a un video permitido.')
        return 'video'

    raise ValidationError('El archivo no es una imagen o un video permitido.')
