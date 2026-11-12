"""Erros de negócio da aplicação, com mensagens adequadas à camada superior."""


class AppError(Exception):
    """Erro base: a mensagem pode ser exibida ao usuário."""


class InvalidDataError(AppError):
    """Dados informados inválidos (campo vazio, formato errado etc.)."""


class NotFoundError(AppError):
    """Registro não encontrado."""


class ConflictError(AppError):
    """Conflito com algo que já existe (e-mail duplicado, por exemplo)."""


class UnauthorizedError(AppError):
    """Usuário não autenticado ou sessão inválida/expirada."""


class ForbiddenError(AppError):
    """Usuário autenticado, mas sem permissão para a ação."""
