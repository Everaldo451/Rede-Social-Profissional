class ConnectionService:
    def __init__(
        self, connection_repository, professional_repository, notification_repository
    ):
        self.connections = connection_repository
        self.professionals = professional_repository
        self.notifications = notification_repository

    def create(self, user_id, connected_user_id, data):
        pass

    def connection_exists(self, user_id, connected_user_id):
        pass

    def request_connection(self, user_id, connected_user_id):
        if user_id == connected_user_id:
            raise ValueError("Escolha outro profissional para se conectar.")
        profiles = self.professionals.get_by_ids([user_id, connected_user_id])
        if user_id not in profiles or connected_user_id not in profiles:
            raise ValueError("Os dois profissionais devem estar cadastrados.")
        request_id = self.connections.request_connection(user_id, connected_user_id)
        sender = profiles[user_id]
        self.notifications.create(
            {
                "destinatario_id": connected_user_id,
                "tipo": "nova_conexao",
                "titulo": f"Solicitação de conexão de {sender.get('nome', 'um profissional')}",
                "referencia_tipo": "usuario",
                "referencia_id": user_id,
            }
        )
        return request_id

    def list_all(self):
        pass

    def get_paginated_for_user(self, user_id, offset, limit):
        ids = self.connections.get_paginated_for_user(user_id, offset, limit)
        profiles = self.professionals.get_by_ids(ids)
        return [profiles[person_id] for person_id in ids if person_id in profiles]

    def update_connection_request(self, user_id, connected_user_id, data):
        status = "aceita" if data.acao == "aceitar" else "recusada"
        changed = self.connections.update_connection_request(
            user_id, connected_user_id, str(data.solicitacao_id), status
        )
        if changed and status == "aceita":
            recipient = self.professionals.get_by_ids([user_id]).get(user_id, {})
            self.notifications.create(
                {
                    "destinatario_id": connected_user_id,
                    "tipo": "conexao_aceita",
                    "titulo": (
                        f"{recipient.get('nome', 'Um profissional')} "
                        "aceitou sua solicitação de conexão"
                    ),
                    "referencia_tipo": "usuario",
                    "referencia_id": user_id,
                }
            )
        return status

    def get_mutual_connections(self, user_id, connected_user_id):
        pass

    def get_shortest_path(self, user_id, target_user_id):
        if user_id == target_user_id:
            raise ValueError("Selecione outro profissional para calcular a distância.")
        result = self.connections.get_shortest_path(user_id, target_user_id)
        if result is None:
            return None
        profiles = self.professionals.get_by_ids(result["ids"])
        return {
            "graus": result["graus"],
            "nomes": [
                profiles.get(person_id, {}).get("nome", "Profissional indisponível")
                for person_id in result["ids"]
            ],
        }

    def count_connections(self, user_id):
        return self.connections.count_connections(user_id)

    def update(self, user_id, connected_user_id, data):
        pass

    def delete(self, user_id, connected_user_id):
        pass

    def list_requests(self, user_id):
        requests = self.connections.list_requests(user_id)
        other_ids = {
            item["remetente_id"] if item["destinatario_id"] == user_id
            else item["destinatario_id"]
            for item in requests
        }
        profiles = self.professionals.get_by_ids(other_ids)
        for item in requests:
            item["recebida"] = item["destinatario_id"] == user_id
            other_id = item["remetente_id"] if item["recebida"] else item["destinatario_id"]
            item["nome"] = profiles.get(other_id, {}).get("nome", "Profissional indisponível")
        return requests

    def search_professionals(self, user_id, filters):
        return self.professionals.search(user_id, filters.nome.strip(), filters.habilidade_id)
