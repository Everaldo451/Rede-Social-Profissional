class ConnectionService:
    def __init__(self, connection_repository):
        pass

    def create(self, user_id, connected_user_id, data):
        pass

    def connection_exists(self, user_id, connected_user_id):
        pass

    def request_connection(self, user_id, connected_user_id):
        pass

    def list_all(self):
        pass

    def get_paginated_for_user(self, user_id, offset, limit):
        pass

    def update_connection_request(self, user_id, connected_user_id, data):
        pass

    def get_mutual_connections(self, user_id, connected_user_id):
        pass

    def get_shortest_path(self, user_id, target_user_id):
        pass

    def count_connections(self, user_id):
        pass

    def update(self, user_id, connected_user_id, data):
        pass

    def delete(self, user_id, connected_user_id):
        pass
