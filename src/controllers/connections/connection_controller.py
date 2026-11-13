# Camada de entrada das operações de conexões entre profissionais; conecta a interface aos serviços.
from dto.connections.request.network_requests import (
    ConnectionDecisionRequest,
    ProfessionalSearchRequest,
)

from ._response import run_action


class ConnectionController:
    def __init__(self, connection_service):
        self.service = connection_service

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def create(self, user_id, connected_user_id, data):
        pass

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def connection_exists(self, user_id, connected_user_id):
        pass

    # Encaminha a solicitação de conexão entre os dois profissionais.
    def request_connection(self, user_id, connected_user_id):
        return run_action(
            self.service.request_connection, user_id, connected_user_id
        )

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def list_all(self):
        pass

    # Solicita uma página das conexões do usuário.
    def get_paginated_for_user(self, user_id, offset, limit):
        return run_action(
            self.service.get_paginated_for_user, user_id, offset, limit
        )

    # Valida a decisão de aceitar ou recusar antes de encaminhá-la ao serviço.
    def update_connection_request(self, user_id, connected_user_id, data):
        return run_action(
            lambda: self.service.update_connection_request(
                user_id, connected_user_id, ConnectionDecisionRequest.model_validate(data)
            )
        )

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def get_mutual_connections(self, user_id, connected_user_id):
        pass

    # Solicita a menor distância de conexões até o profissional escolhido.
    def get_shortest_path(self, user_id, target_user_id):
        return run_action(self.service.get_shortest_path, user_id, target_user_id)

    # Consulta a quantidade de conexões do usuário.
    def count_connections(self, user_id):
        return run_action(self.service.count_connections, user_id)

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def update(self, user_id, connected_user_id, data):
        pass

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def delete(self, user_id, connected_user_id):
        pass

    # Obtém as solicitações relacionadas ao usuário informado.
    def list_requests(self, user_id):
        return run_action(self.service.list_requests, user_id)

    # Valida os filtros de nome e habilidade usados na busca de profissionais.
    def search_professionals(self, user_id, data):
        return run_action(
            lambda: self.service.search_professionals(
                user_id, ProfessionalSearchRequest.model_validate(data)
            )
        )
