# Regras de curtidas e notificação do autor da publicação.
from common.errors import NotFoundError, UnauthorizedError


class LikeService:
    def __init__(self, repository, post_repository, user_repository, notification_service=None):
        self._repo = repository
        self._posts = post_repository
        self._users = user_repository
        self._notifications = notification_service

    # Valida usuário e publicação; notifica outro autor somente quando ainda não havia essa curtida.
    def create(self, user_id, post_id):
        author = self._users.get_by_id(user_id)
        if not author:
            raise UnauthorizedError("Entre para curtir uma publicação.")
        post = self._posts.get_by_id(post_id)
        if not post:
            raise NotFoundError("Publicação não encontrada.")

        already_liked = any(
            str(like["user_id"]) == str(user_id)
            for like in self._repo.get_by_post_id(post_id)
        )
        like = self._repo.create(user_id, post_id)
        if (
            self._notifications
            and not already_liked
            and str(post["author_id"]) != str(user_id)
        ):
            author_name = author.get("name") or author.get("nome") or "Um profissional"
            self._notifications.create(
                {
                    "destinatario_id": post["author_id"],
                    "tipo": "curtida",
                    "titulo": f"{author_name} curtiu sua publicação",
                    "referencia_tipo": "post",
                    "referencia_id": post_id,
                }
            )
        return like

    # Retorna a curtida ou sinaliza que o registro não foi encontrado.
    def get_by_id(self, like_id):
        item = self._repo.get_by_id(like_id)
        if not item:
            raise NotFoundError("Curtida não encontrada.")
        return item

    # Lista as curtidas associadas à publicação.
    def get_by_post_id(self, post_id):
        return self._repo.get_by_post_id(post_id)

    # Remove a curtida identificada pelo par usuário e publicação.
    def delete_user_like(self, user_id, post_id):
        return self._repo.delete_user_like(user_id, post_id)

    # Delega a exclusão da curtida pelo identificador.
    def delete(self, like_id):
        return self._repo.delete(like_id)
