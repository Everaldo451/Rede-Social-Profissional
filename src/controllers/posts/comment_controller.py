# Camada de entrada das operações de comentários; conecta a interface aos serviços.
from controllers.shared.response_handler import run
from dto.posts.request.post_requests import CreateCommentRequest


class CommentController:
    def __init__(self, comment_service):
        self._service = comment_service

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, author_id, post_id, data: dict):
        return run(lambda: self._service.create(author_id, post_id, CreateCommentRequest(**data)))

    # Solicita os comentários associados à publicação.
    def list_by_post(self, post_id):
        return run(lambda: self._service.list_by_post(post_id))
