from datetime import datetime, timezone

import pytest
from bson import ObjectId

USER_ID = ObjectId("671a2b3c4d5e6f7890123456")
SKILL_ID = ObjectId("671a2b3c4d5e6f7890124601")
ORGANIZATION_ID = ObjectId("671a2b3c4d5e6f7890124201")
INSTITUTION_ID = ObjectId("671a2b3c4d5e6f7890124202")
ISSUER_ID = ObjectId("671a2b3c4d5e6f7890124203")
CREATED_AT = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
UPDATED_AT = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)


class RepositoryTestResources:
    def __init__(self, mongo_database, neo4j_session_factory):
        self.mongo = mongo_database
        self.neo4j_session_factory = neo4j_session_factory
        self.ids = {
            "user": str(ObjectId()),
            "skill": str(ObjectId()),
            "organization": str(ObjectId()),
            "institution": str(ObjectId()),
            "issuer": str(ObjectId()),
        }
        self._mongo_ids = {}
        self._mongo_filters = {}
        self._neo4j_ids = set()

    def track_document(self, collection_name, document_id):
        self._mongo_ids.setdefault(collection_name, set()).add(
            ObjectId(str(document_id))
        )

    def track_filter(self, collection_name, filter_document):
        self._mongo_filters.setdefault(collection_name, []).append(filter_document)

    def insert_document(self, collection_name, document):
        self.track_document(collection_name, document["_id"])
        return self.mongo[collection_name].insert_one(document)

    def track_graph_nodes(self, *node_ids):
        self._neo4j_ids.update(str(node_id) for node_id in node_ids)

    def cleanup(self):
        try:
            if self._neo4j_ids:
                with self.neo4j_session_factory() as session:
                    session.run(
                        """
                        MATCH (node)
                        WHERE node.id IN $ids
                        DETACH DELETE node
                        """,
                        ids=list(self._neo4j_ids),
                    ).consume()
        finally:
            for collection_name, document_ids in self._mongo_ids.items():
                if document_ids:
                    self.mongo[collection_name].delete_many(
                        {"_id": {"$in": list(document_ids)}}
                    )
            for collection_name, filters in self._mongo_filters.items():
                for filter_document in filters:
                    self.mongo[collection_name].delete_many(filter_document)


@pytest.fixture
def ids():
    return {
        "user": str(USER_ID),
        "skill": str(SKILL_ID),
        "organization": str(ORGANIZATION_ID),
        "institution": str(INSTITUTION_ID),
        "issuer": str(ISSUER_ID),
    }


@pytest.fixture
def user_record(ids):
    return {
        "_id": ids["user"],
        "nome": "Ana Silva",
        "nome_normalizado": "ana silva",
        "email": "ana@example.com",
        "senha": "$2b$12$test-hash-value",
        "headline": "Desenvolvedora Backend",
        "resumo": "Desenvolve APIs e serviços para produtos digitais.",
        "localizacao": "João Pessoa, PB",
        "nivel_carreira": "Pleno",
        "aceita_mentoria": True,
        "habilidades": [
            {
                "habilidade_id": ids["skill"],
                "nivel": "intermediario",
                "anos_experiencia": 2,
            }
        ],
        "experiencias": [
            {
                "organizacao_id": ids["organization"],
                "cargo": "Desenvolvedora Backend",
                "data_inicio": datetime(2024, 3, 1, tzinfo=timezone.utc),
                "data_fim": None,
                "atual": True,
                "descricao": "Desenvolvimento de APIs REST",
            }
        ],
        "formacao": [
            {
                "instituicao_id": ids["institution"],
                "curso": "Ciência da Computação",
                "grau": "bacharelado",
                "ano_inicio": 2022,
                "ano_conclusao": None,
            }
        ],
        "certificacoes": [
            {
                "nome": "AWS Cloud Practitioner",
                "emissor_id": ids["issuer"],
                "data_emissao": datetime(2025, 6, 15, tzinfo=timezone.utc),
                "url": "https://example.com/certificado",
            }
        ],
        "criado_em": CREATED_AT,
        "atualizado_em": UPDATED_AT,
    }


@pytest.fixture
def skill_record(ids):
    return {
        "_id": ids["skill"],
        "nome": "Python",
        "nome_normalizado": "python",
        "categoria": "Linguagem de Programação",
        "descricao": (
            "Linguagem de programação de alto nível usada em desenvolvimento "
            "web, automação e ciência de dados."
        ),
        "criado_em": CREATED_AT,
        "atualizado_em": UPDATED_AT,
    }


@pytest.fixture
def organization_record(ids):
    return {
        "_id": ids["organization"],
        "nome": "Tech Solutions",
        "nome_normalizado": "tech solutions",
        "tipos": ["empresa"],
        "setor": "Tecnologia",
        "site": "https://example.com",
        "cidade": "João Pessoa",
        "estado": "PB",
        "status_verificacao": "pendente",
        "criado_por_usuario_id": ids["user"],
        "criado_em": CREATED_AT,
    }


@pytest.fixture
def repository_resources():
    from src.database.mongo import get_mongo_database
    from src.database.neo4j import get_neo4j_session

    resources = RepositoryTestResources(
        get_mongo_database(), get_neo4j_session
    )
    yield resources
    resources.cleanup()
