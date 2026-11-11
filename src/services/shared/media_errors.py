class MediaError(Exception):
    """Base exception for media operations."""


class MediaValidationError(MediaError, ValueError):
    """Raised when media data is invalid outside the controller boundary."""


class MediaPersistenceError(MediaError):
    """Raised when MongoDB or GridFS cannot complete a media operation."""
