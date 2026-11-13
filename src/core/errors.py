"""Erros de domínio. Os controllers os convertem em mensagens para a interface."""


class AppError(Exception):
    """Erro esperado de regra de negócio."""


class ValidationFailed(AppError):
    pass


class AuthenticationFailed(AppError):
    pass


class PermissionDenied(AppError):
    pass


class NotFound(AppError):
    pass
