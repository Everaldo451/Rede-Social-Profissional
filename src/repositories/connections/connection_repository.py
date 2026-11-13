# Persiste solicitações e conexões no Neo4j e consulta caminhos na rede profissional.
from uuid import uuid4


class ConnectionRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    # Ordena o par de usuários e força um bloqueio de escrita para coordenar solicitações concorrentes.
    @staticmethod
    def _lock_pair(tx, user_id, other_id):
        first_id, second_id = sorted((user_id, other_id))
        # Solicitações em sentidos opostos precisam adquirir o mesmo lock.
        tx.run(
            """
            MERGE (first:Pessoa {id: $first_id})
            SET first._conexao_lock = true
            REMOVE first._conexao_lock
            MERGE (:Pessoa {id: $second_id})
            """,
            first_id=first_id,
            second_id=second_id,
        ).consume()

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def create(self, user_id, connected_user_id, data):
        pass

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def connection_exists(self, user_id, connected_user_id):
        pass

    # Executa uma transação que verifica duplicidade e cria o convite de conexão.
    def request_connection(self, user_id, connected_user_id):
        request_id = str(uuid4())

        # Revalida o par dentro da transação e registra apenas uma solicitação pendente.
        def register(tx):
            self._lock_pair(tx, user_id, connected_user_id)
            existing = tx.run(
                """
                MATCH (sender:Pessoa {id: $sender_id}), (receiver:Pessoa {id: $receiver_id})
                OPTIONAL MATCH (sender)-[request:SOLICITOU_CONEXAO]-(receiver)
                WHERE request.status = 'pendente' OR request.id = $request_id
                RETURN request.id AS request_id,
                       exists((sender)-[:CONECTADO_COM]-(receiver)) AS connected
                LIMIT 1
                """,
                sender_id=user_id,
                receiver_id=connected_user_id,
                request_id=request_id,
            ).single(strict=True)
            if existing["request_id"] == request_id:
                return request_id
            if existing["connected"]:
                raise ValueError("Vocês já estão conectados.")
            if existing["request_id"]:
                raise ValueError("Já existe uma solicitação pendente entre vocês.")

            tx.run(
                """
                MATCH (sender:Pessoa {id: $sender_id}), (receiver:Pessoa {id: $receiver_id})
                CREATE (sender)-[:SOLICITOU_CONEXAO {
                    id: $request_id, status: 'pendente',
                    criado_em: timestamp(), atualizado_em: timestamp()
                }]->(receiver)
                """,
                sender_id=user_id,
                receiver_id=connected_user_id,
                request_id=request_id,
            ).consume()
            return request_id

        with self.session_factory() as session:
            return session.execute_write(register)

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def list_all(self):
        pass

    # Lista os identificadores das conexões diretas com ordenação e paginação no grafo.
    def get_paginated_for_user(self, user_id, offset, limit):
        with self.session_factory() as session:
            rows = session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (:Pessoa {id: $user_id})-[:CONECTADO_COM]-(other:Pessoa)
                    RETURN DISTINCT other.id AS id ORDER BY id SKIP $offset LIMIT $limit
                    """,
                    user_id=user_id,
                    offset=offset,
                    limit=limit,
                ).data()
            )
        return [row["id"] for row in rows]

    # Atualiza a resposta do destinatário e cria a conexão quando o convite é aceito.
    def update_connection_request(self, user_id, connected_user_id, request_id, status):
        # Confere destinatário e estado do convite antes de gravar a decisão na mesma transação.
        def respond(tx):
            self._lock_pair(tx, user_id, connected_user_id)
            params = {
                "sender_id": connected_user_id,
                "receiver_id": user_id,
                "request_id": request_id,
                "status": status,
            }
            existing = tx.run(
                """
                MATCH (:Pessoa {id: $sender_id})-[r:SOLICITOU_CONEXAO {id: $request_id}]->
                      (:Pessoa {id: $receiver_id})
                RETURN r.status AS status
                """,
                **params,
            ).single()
            if existing is None or existing["status"] not in {"pendente", status}:
                raise ValueError("Solicitação pendente não encontrada para o destinatário.")
            if existing["status"] == status:
                return False

            tx.run(
                """
                MATCH (sender:Pessoa {id: $sender_id})-[r:SOLICITOU_CONEXAO {id: $request_id}]->
                      (receiver:Pessoa {id: $receiver_id})
                SET r.status = $status, r.atualizado_em = timestamp()
                FOREACH (_ IN CASE WHEN $status = 'aceita' THEN [1] ELSE [] END |
                    MERGE (sender)-[c:CONECTADO_COM]-(receiver)
                    ON CREATE SET c.criado_em = timestamp()
                )
                """,
                **params,
            ).consume()
            return True

        with self.session_factory() as session:
            return session.execute_write(respond)

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def get_mutual_connections(self, user_id, connected_user_id):
        pass

    # Usa shortestPath para obter o caminho mínimo e seu número de conexões.
    def get_shortest_path(self, user_id, target_user_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (origin:Pessoa {id: $user_id}), (target:Pessoa {id: $target_id})
                    WHERE origin <> target
                    MATCH path = shortestPath((origin)-[:CONECTADO_COM*]-(target))
                    RETURN [person IN nodes(path) | person.id] AS ids, length(path) AS graus
                    """,
                    user_id=user_id,
                    target_id=target_user_id,
                ).single()
            )

    # Conta os profissionais distintos conectados diretamente ao usuário.
    def count_connections(self, user_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (:Pessoa {id: $user_id})-[:CONECTADO_COM]-(other:Pessoa)
                    RETURN count(DISTINCT other) AS total
                    """,
                    user_id=user_id,
                ).single(strict=True)["total"]
            )

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def update(self, user_id, connected_user_id, data):
        pass

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def delete(self, user_id, connected_user_id):
        pass

    # Lista convites pendentes enviados ou recebidos, excluindo pares que já estão conectados.
    def list_requests(self, user_id):
        with self.session_factory() as session:
            return session.execute_read(
                lambda tx: tx.run(
                    """
                    MATCH (sender:Pessoa)-[r:SOLICITOU_CONEXAO]->(receiver:Pessoa)
                    WHERE (sender.id = $user_id OR receiver.id = $user_id)
                      AND r.status = 'pendente'
                      AND NOT exists((sender)-[:CONECTADO_COM]-(receiver))
                    RETURN r.id AS id, r.status AS status, r.criado_em AS criado_em,
                           sender.id AS remetente_id, receiver.id AS destinatario_id
                    ORDER BY r.criado_em DESC, r.id
                    """,
                    user_id=user_id,
                ).data()
            )
