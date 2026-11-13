# Regras de acesso ao histórico de notificações e às operações de leitura.
# Sinaliza que a notificação solicitada não foi encontrada.
class NotificationNotFoundError(Exception):
    """A notificação não existe."""


# Sinaliza uma tentativa de acessar a notificação de outro destinatário.
class NotificationPermissionError(Exception):
    """A notificação pertence a outro usuário."""


class NotificationService:
    def __init__(self, notification_repository):
        self.notification_repository = notification_repository

    def _get_owned(self, notification_id, user_id=None):
        """Busca a notificação e confere o dono (NF006), quando user_id é informado."""
        notification = self.notification_repository.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError("Notificação não encontrada.")
        if user_id is not None and notification["destinatario_id"] != str(user_id):
            raise NotificationPermissionError(
                "Você não tem permissão para acessar esta notificação."
            )
        return notification

    # Delega a gravação de uma notificação ao repositório.
    def create(self, data):
        return self.notification_repository.create(data)

    # Busca a notificação com a verificação de destinatário quando o usuário é informado.
    def get_by_id(self, notification_id, user_id=None):
        return self._get_owned(notification_id, user_id)

    # Consulta uma página do histórico usando os filtros recebidos.
    def get_paginated(self, offset, limit, filters=None):
        return self.notification_repository.get_paginated(offset, limit, filters)

    # Consulta o contador de notificações não lidas do destinatário.
    def count_unread_by_user_id(self, user_id):
        return self.notification_repository.count_unread_by_user_id(user_id)

    # Solicita a atualização de todas as notificações do usuário para lidas.
    def mark_all_as_read(self, user_id):
        return self.notification_repository.mark_all_as_read(user_id)

    # Confere a existência e, quando informado, o destinatário antes de alterar a notificação.
    def update(self, notification_id, data, user_id=None):
        self._get_owned(notification_id, user_id)
        return self.notification_repository.update(notification_id, data)

    # Confere a existência e, quando informado, o destinatário antes de excluir a notificação.
    def delete(self, notification_id, user_id=None):
        self._get_owned(notification_id, user_id)
        return self.notification_repository.delete(notification_id)
