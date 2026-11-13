# Distingue erros de validação de mídia e falhas ao persistir seus arquivos.
from common.errors import AppError, InvalidDataError


# Exceção base para as falhas específicas do módulo de mídia.
class MediaError(AppError):
    """Base exception for media operations."""


# Representa um arquivo ou parâmetro de mídia inválido.
class MediaValidationError(InvalidDataError):
    """Raised when media data is invalid outside the controller boundary."""


# Representa uma falha na operação de armazenamento ou leitura.
class MediaPersistenceError(MediaError):
    """Raised when MongoDB or GridFS cannot complete a media operation."""
