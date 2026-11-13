# Camada de entrada das operações de publicações; conecta a interface aos serviços.
from controllers.shared.response_handler import run
from dto.posts.request.post_requests import CreatePostRequest, UpdatePostRequest


class PostController:
    def __init__(self, post_service):
        self._service = post_service

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, author_id, data: dict, files=()):
        return run(lambda: self._service.create(author_id, CreatePostRequest(**data), files))

    # Solicita ao serviço o registro identificado e devolve o resultado à interface.
    def get_by_id(self, post_id):
        return run(lambda: self._service.get_by_id(post_id))

    # Encaminha posição inicial, tamanho da página e filtros para a consulta.
    def get_paginated(self, offset, limit, filters=None):
        return run(lambda: self._service.get_paginated(offset, limit, filters))

    # Encaminha a consulta da lista completa ao serviço.
    def list_all(self):
        return run(self._service.list_all)

    # Encaminha a atualização ao serviço após validar os dados de entrada.
    def update(self, requester_id, post_id, data: dict, new_files=()):
        return run(
            lambda: self._service.update(requester_id, post_id, UpdatePostRequest(**data), new_files)
        )

    # Solicita a remoção do registro e devolve uma resposta à interface.
    def delete(self, requester_id, post_id):
        return run(lambda: self._service.delete(requester_id, post_id))
