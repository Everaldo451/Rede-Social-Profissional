from dto.connections.request.network_requests import (
    ConnectionDecisionRequest,
    ProfessionalSearchRequest,
)

from ._response import run_action


class ConnectionController:
    def __init__(self, connection_service):
        self.service = connection_service

    def create(self, user_id, connected_user_id, data):
        pass

    def connection_exists(self, user_id, connected_user_id):
        pass

    def request_connection(self, user_id, connected_user_id):
        return run_action(
            self.service.request_connection, user_id, connected_user_id
        )

    def list_all(self):
        pass

    def get_paginated_for_user(self, user_id, offset, limit):
        return run_action(
            self.service.get_paginated_for_user, user_id, offset, limit
        )

    def update_connection_request(self, user_id, connected_user_id, data):
        return run_action(
            lambda: self.service.update_connection_request(
                user_id, connected_user_id, ConnectionDecisionRequest.model_validate(data)
            )
        )

    def get_mutual_connections(self, user_id, connected_user_id):
        pass

    def get_shortest_path(self, user_id, target_user_id):
        return run_action(self.service.get_shortest_path, user_id, target_user_id)

    def count_connections(self, user_id):
        return run_action(self.service.count_connections, user_id)

    def update(self, user_id, connected_user_id, data):
        pass

    def delete(self, user_id, connected_user_id):
        pass

    def list_requests(self, user_id):
        return run_action(self.service.list_requests, user_id)

    def search_professionals(self, user_id, data):
        return run_action(
            lambda: self.service.search_professionals(
                user_id, ProfessionalSearchRequest.model_validate(data)
            )
        )
