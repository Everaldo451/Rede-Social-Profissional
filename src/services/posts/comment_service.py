from datetime import datetime, timezone

from core.errors import AuthenticationFailed, NotFound, PermissionDenied
from services.shared.presenters import comment_view


class CommentService:
    def __init__(self, comment_repository, post_repository, user_repository, allow_self_comment=False, notification_service=None):
        self._comments = comment_repository
        self._posts = post_repository
        self._users = user_repository
        # RF012: comentários em publicações de *outros* usuários.
        self._allow_self_comment = allow_self_comment
        self._notifications = notification_service

    def create(self, author_id, post_id, data):
        author = self._users.get_by_id(author_id)
        if not author:
            raise AuthenticationFailed("Você precisa estar autenticado para comentar.")
        post = self._posts.get_by_id(post_id)
        if not post:
            raise NotFound("Publicação não encontrada.")
        if post["author_id"] == author_id and not self._allow_self_comment:
            raise PermissionDenied("Você só pode comentar publicações de outros usuários.")
        comment = self._comments.create(
            {
                "post_id": post_id,
                "author_id": author_id,
                "text": data.text,
                "created_at": datetime.now(timezone.utc),
            }
        )
        if self._notifications:
            self._notifications.create({
                "user_id": post["author_id"],
                "title": "Novo comentário na sua publicação",
                "message": f"{author['name']} comentou: {data.text[:180]}",
                "kind": "comment",
            })
        return comment_view({author["id"]: author}, comment)

    def list_by_post(self, post_id):
        comments = self._comments.list_by_post_ids([post_id]).get(post_id, [])
        users = self._users.get_many_by_ids({c["author_id"] for c in comments})
        return [comment_view(users, c) for c in comments]
