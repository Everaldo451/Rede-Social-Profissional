from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock

from bson import ObjectId

from src.controllers.connections.connection_controller import ConnectionController
from src.database import get_mongo_database, get_neo4j_session
from src.repositories.connections.connection_repository import ConnectionRepository
from src.repositories.connections.professional_repository import ProfessionalRepository
from src.services.connections.connection_service import ConnectionService


def test_concurrent_requests_and_recipient_only_decision():
    db = get_mongo_database()
    ids = [ObjectId() for _ in range(3)]
    ana, bruno, carla = map(str, ids)
    people = [
        {"_id": object_id, "nome": name, "email": f"{object_id}@exemplo.test"}
        for object_id, name in zip(ids, ("Ana", "Bruno", "Carla"))
    ]
    db.usuarios.insert_many(people)

    try:
        with get_neo4j_session() as session:
            session.run(
                """
                CREATE (:Pessoa {id: $ana})
                CREATE (bruno:Pessoa {id: $bruno})-[:CONECTADO_COM]->(carla:Pessoa {id: $carla})
                """,
                ana=ana,
                bruno=bruno,
                carla=carla,
            ).consume()

        controller = ConnectionController(
            ConnectionService(
                ConnectionRepository(get_neo4j_session),
                ProfessionalRepository(db),
                notification_repository=Mock(),
            )
        )
        start = Barrier(2)

        def send(sender, receiver):
            start.wait(timeout=10)
            return controller.request_connection(sender, receiver)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(send, ana, bruno)
            second = pool.submit(send, bruno, ana)
            outgoing = first.result()
            incoming = second.result()

        assert outgoing.status != incoming.status
        sender, recipient = (ana, bruno) if outgoing.status else (bruno, ana)
        request_id = outgoing.data if outgoing.status else incoming.data
        request = {"solicitacao_id": request_id, "acao": "aceitar"}
        assert controller.get_shortest_path(ana, carla).data is None
        assert not controller.update_connection_request(sender, recipient, request).status
        assert controller.update_connection_request(recipient, sender, request).status
        assert controller.update_connection_request(recipient, sender, request).status
        assert not controller.update_connection_request(
            recipient, sender, {**request, "acao": "recusar"}
        ).status
        assert not controller.request_connection(ana, bruno).status
        assert controller.count_connections(ana).data == 1
        assert controller.get_shortest_path(ana, carla).data == {
            "graus": 2, "nomes": ["Ana", "Bruno", "Carla"]
        }
    finally:
        with get_neo4j_session() as session:
            session.run(
                "MATCH (p:Pessoa) WHERE p.id IN $ids DETACH DELETE p",
                ids=[ana, bruno, carla],
            ).consume()
        db.usuarios.delete_many({"_id": {"$in": ids}})
