from common.errors import AppError, InvalidDataError


class MediaError(AppError):
    """Base exception for media operations."""


class MediaValidationError(InvalidDataError):
    """Raised when media data is invalid outside the controller boundary."""


class MediaPersistenceError(MediaError):
    """Raised when MongoDB or GridFS cannot complete a media operation."""
