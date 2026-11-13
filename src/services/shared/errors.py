"""Erros esperados das regras de negócio."""


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
