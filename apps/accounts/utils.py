import logging

from django.core.exceptions import SuspiciousFileOperation

logger = logging.getLogger(__name__)


def safe_file_size(field):
    if not field:
        return 0
    try:
        return field.size
    except (OSError, AttributeError, ValueError, SuspiciousFileOperation) as exc:
        logger.warning('No se pudo leer el tamaño del archivo: %s', exc)
        return 0
