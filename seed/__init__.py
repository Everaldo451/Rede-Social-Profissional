"""Load the JSON seed collections into MongoDB and refresh unread counters."""

from pathlib import Path
from typing import Any

import bcrypt
from bson import json_util
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from redis import Redis

from src.database import get_mongo_database, get_neo4j_session, get_redis_client


COLLECTIONS_DIR = Path(__file__).parent / "collections"
COLLECTION_ORDER = (
    "habilidades",
    "organizacoes",
    "usuarios",
    "posts",
    "comentarios",
    "curtidas",
    "mentorias",
    "notificacoes",
    "midias.files",
)
RELATIONSHIPS_DIR = Path(__file__).parent / "rellationships"
GRAPH_RELATIONSHIPS = {
    "CONECTADO_COM": "Pessoa",
    "POSSUI_HABILIDADE": "Habilidade",
    "DESEJA_DESENVOLVER": "Habilidade",
    "TRABALHOU_EM": "Organizacao",
    "ESTUDOU_EM": "Organizacao",
    "MEMBRO_DE": "Organizacao",
    "ENSINA": "Habilidade",
    "SOLICITOU_CONEXAO": "Pessoa",
    "MENTORA": "Pessoa",
}
RELATIONSHIP_PROPERTIES = {
    "CONECTADO_COM": {"desde", "origem"},
    "POSSUI_HABILIDADE": {"nivel"},
    "DESEJA_DESENVOLVER": {"desde", "nivel"},
    "TRABALHOU_EM": {"cargo", "data_inicio", "data_fim", "atual"},
    "ESTUDOU_EM": {"curso", "grau", "ano_inicio", "ano_conclusao"},
    "MEMBRO_DE": {"papel", "status", "desde"},
    "ENSINA": {"nivel", "experiencia_anos"},
    "SOLICITOU_CONEXAO": {"status", "criada_em", "atualizada_em"},
    "MENTORA": {"status", "criada_em", "atualizada_em"},
}
FILE_RELATIONSHIPS = (
    "CONECTADO_COM",
    "SOLICITOU_CONEXAO",
    "MEMBRO_DE",
    "ENSINA",
)


def load_collections(
    collections_dir: Path = COLLECTIONS_DIR,
) -> dict[str, list[dict[str, Any]]]:
    """Load and validate the Extended JSON documents in the collections directory."""
    collections: dict[str, list[dict[str, Any]]] = {}
    for collection_name in COLLECTION_ORDER:
        collection_path = collections_dir / f"{collection_name}.json"
        documents = json_util.loads(collection_path.read_text(encoding="utf-8"))
        if not isinstance(documents, list) or any(
            not isinstance(document, dict) or "_id" not in document
            for document in documents
        ):
            raise ValueError(
                f"{collection_path} must contain a JSON array of documents with _id"
            )
        document_ids = [document["_id"] for document in documents]
        if len(set(document_ids)) != len(document_ids):
            raise ValueError(f"{collection_path} contains duplicate _id values")
        collections[collection_name] = documents
    return collections


def load_relationships(
    relationships_dir: Path = RELATIONSHIPS_DIR,
) -> dict[str, list[dict[str, Any]]]:
    """Load relationships whose data does not belong to a MongoDB collection."""
    relationships: dict[str, list[dict[str, Any]]] = {}
    for relationship_type in FILE_RELATIONSHIPS:
        relationship_path = relationships_dir / f"{relationship_type}.json"
        documents = json_util.loads(relationship_path.read_text(encoding="utf-8"))
        if not isinstance(documents, list):
            raise ValueError(f"{relationship_path} must contain a JSON array")
        for document in documents:
            if not isinstance(document, dict) or not {
                "source_id",
                "target_id",
                "properties",
            }.issubset(document):
                raise ValueError(
                    f"{relationship_path} entries must contain source_id, "
                    "target_id, and properties"
                )
            if set(document["properties"]) != RELATIONSHIP_PROPERTIES[relationship_type]:
                raise ValueError(
                    f"{relationship_path} properties must be exactly "
                    f"{sorted(RELATIONSHIP_PROPERTIES[relationship_type])}"
                )
        relationships[relationship_type] = documents
    return relationships


def import_collections(
    database: Database, collections: dict[str, list[dict[str, Any]]]
) -> None:
    """Upsert seed documents without deleting records outside the seed set."""
    for collection_name in COLLECTION_ORDER:
        documents = collections[collection_name]
        collection = database[collection_name]
        for document in documents:
            collection.replace_one({"_id": document["_id"]}, document, upsert=True)
        print(f"{collection_name}: {len(documents)} documentos carregados")


def hash_seed_passwords(collections: dict[str, list[dict[str, Any]]]) -> None:
    """Hash plaintext fixture passwords with bcrypt before importing them."""
    for user in collections["usuarios"]:
        password = user["senha"]
        if password.startswith(("$2a$", "$2b$", "$2y$")):
            continue

        encoded_password = password.encode("utf-8")
        if len(encoded_password) > 72:
            raise ValueError(
                f"Seed password for {user['email']} must not exceed 72 UTF-8 bytes"
            )
        user["senha"] = bcrypt.hashpw(
            encoded_password, bcrypt.gensalt()
        ).decode("ascii")


def create_indexes(database: Database) -> None:
    """Create the indexes specified for the seed collections."""
    database["usuarios"].create_index("email", unique=True)
    database["usuarios"].create_index("nome")
    database["habilidades"].create_index("nome_normalizado")
    database["organizacoes"].create_index("nome_normalizado")
    database["posts"].create_index([("criado_em", DESCENDING)])
    database["posts"].create_index(
        [("autor_id", ASCENDING), ("criado_em", DESCENDING)]
    )
    database["comentarios"].create_index(
        [("post_id", ASCENDING), ("criado_em", DESCENDING)]
    )
    database["curtidas"].create_index(
        [("usuario_id", ASCENDING), ("post_id", ASCENDING)], unique=True
    )


def sync_unread_notification_counts(
    database: Database,
    redis_client: Redis,
    collections: dict[str, list[dict[str, Any]]],
) -> None:
    """Refresh only notifications:unread keys for users touched by this seed."""
    recipient_ids = {
        document["destinatario_id"]
        for document in collections["notificacoes"]
        if "destinatario_id" in document
    }
    recipient_ids.update(document["_id"] for document in collections["usuarios"])
    if not recipient_ids:
        return

    unread_counts = {recipient_id: 0 for recipient_id in recipient_ids}
    pipeline = [
        {
            "$match": {
                "destinatario_id": {"$in": list(recipient_ids)},
                "lida": False,
            }
        },
        {"$group": {"_id": "$destinatario_id", "count": {"$sum": 1}}},
    ]
    for result in database["notificacoes"].aggregate(pipeline):
        unread_counts[result["_id"]] = result["count"]

    redis_values = {
        f"notifications:unread:{recipient_id}": str(count)
        for recipient_id, count in unread_counts.items()
    }
    if not redis_client.mset(redis_values):
        raise RuntimeError(
            "Redis did not confirm the unread notification counters update"
        )
    print(f"Redis: {len(redis_values)} contadores notifications:unread atualizados")


def build_graph_data(
    collections: dict[str, list[dict[str, Any]]],
    file_relationships: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build Neo4j nodes and relationships from the MongoDB seed documents."""
    if file_relationships is None:
        file_relationships = load_relationships()

    graph_data: dict[str, list[dict[str, Any]]] = {
        "people": [
            {"id": str(user["_id"])}
            for user in collections["usuarios"]
        ],
        "organizations": [
            {"id": str(organization["_id"])}
            for organization in collections["organizacoes"]
        ],
        "skills": [
            {"id": str(skill["_id"])}
            for skill in collections["habilidades"]
        ],
        **{relationship_type: [] for relationship_type in GRAPH_RELATIONSHIPS},
    }

    people_ids = {node["id"] for node in graph_data["people"]}
    organization_ids = {node["id"] for node in graph_data["organizations"]}
    skill_ids = {node["id"] for node in graph_data["skills"]}
    skill_levels = {
        (str(user["_id"]), str(skill["habilidade_id"])): skill["nivel"]
        for user in collections["usuarios"]
        for skill in user.get("habilidades", [])
    }

    for user in collections["usuarios"]:
        person_id = str(user["_id"])
        for skill in user.get("habilidades", []):
            skill_id = str(skill["habilidade_id"])
            graph_data["POSSUI_HABILIDADE"].append(
                {
                    "source_id": person_id,
                    "target_id": skill_id,
                    "properties": {"nivel": skill["nivel"]},
                }
            )
        for experience in user.get("experiencias", []):
            graph_data["TRABALHOU_EM"].append(
                {
                    "source_id": person_id,
                    "target_id": str(experience["organizacao_id"]),
                    "properties": {
                        "cargo": experience["cargo"],
                        "data_inicio": experience["data_inicio"],
                        "data_fim": experience["data_fim"],
                        "atual": experience["atual"],
                    },
                }
            )

        for education in user.get("formacao", []):
            graph_data["ESTUDOU_EM"].append(
                {
                    "source_id": person_id,
                    "target_id": str(education["instituicao_id"]),
                    "properties": {
                        "curso": education["curso"],
                        "grau": education["grau"],
                        "ano_inicio": education["ano_inicio"],
                        "ano_conclusao": education["ano_conclusao"],
                    },
                }
            )

    for mentorship in collections["mentorias"]:
        mentorado_id = str(mentorship["mentorado_id"])
        mentor_id = str(mentorship["mentor_id"])
        skill_id = str(mentorship["habilidade_id"])
        requested_at = mentorship["criada_em"]
        graph_data["DESEJA_DESENVOLVER"].append(
            {
                "source_id": mentorado_id,
                "target_id": skill_id,
                "properties": {
                    "desde": requested_at,
                    "nivel": skill_levels.get(
                        (mentorado_id, skill_id),
                        mentorship.get("nivel", "iniciante"),
                    ),
                },
            }
        )
        graph_data["MENTORA"].append(
            {
                "source_id": mentor_id,
                "target_id": mentorado_id,
                "properties": {
                    "status": mentorship["status"],
                    "criada_em": requested_at,
                    "atualizada_em": (
                        mentorship.get("encerrada_em")
                        or mentorship.get("iniciada_em")
                        or requested_at
                    ),
                },
            }
        )

    for relationship_type, documents in file_relationships.items():
        if relationship_type not in FILE_RELATIONSHIPS:
            raise ValueError(
                f"{relationship_type} is not configured for file-based relationships"
            )
        for document in documents:
            if set(document["properties"]) != RELATIONSHIP_PROPERTIES[relationship_type]:
                raise ValueError(
                    f"{relationship_type} properties must be exactly "
                    f"{sorted(RELATIONSHIP_PROPERTIES[relationship_type])}"
                )
            graph_data[relationship_type].append(document)

    target_ids_by_relationship = {
        "CONECTADO_COM": people_ids,
        "POSSUI_HABILIDADE": skill_ids,
        "DESEJA_DESENVOLVER": skill_ids,
        "TRABALHOU_EM": organization_ids,
        "ESTUDOU_EM": organization_ids,
        "MEMBRO_DE": organization_ids,
        "ENSINA": skill_ids,
        "SOLICITOU_CONEXAO": people_ids,
        "MENTORA": people_ids,
    }
    for relationship_type, _ in GRAPH_RELATIONSHIPS.items():
        for relationship in graph_data[relationship_type]:
            if relationship["source_id"] not in people_ids:
                raise ValueError(
                    f"{relationship_type} references an unknown person "
                    f"{relationship['source_id']}"
                )
            if relationship["target_id"] not in target_ids_by_relationship[
                relationship_type
            ]:
                raise ValueError(
                    f"{relationship_type} references an unknown target "
                    f"{relationship['target_id']}"
                )

    return graph_data


def _write_graph(
    transaction: Any, graph_data: dict[str, list[dict[str, Any]]]
) -> None:
    """Upsert graph nodes and edges in one Neo4j transaction."""
    for node_name, label in (
        ("people", "Pessoa"),
        ("organizations", "Organizacao"),
        ("skills", "Habilidade"),
    ):
        transaction.run(
            f"UNWIND $rows AS row MERGE (node:{label} {{id: row.id}})",
            rows=graph_data[node_name],
        ).consume()

    for relationship_type, target_label in GRAPH_RELATIONSHIPS.items():
        rows = graph_data[relationship_type]
        if not rows:
            continue
        expected_properties = RELATIONSHIP_PROPERTIES[relationship_type]
        for row in rows:
            if set(row["properties"]) != expected_properties:
                raise ValueError(
                    f"{relationship_type} properties must be exactly "
                    f"{sorted(expected_properties)}"
                )
        transaction.run(
            "UNWIND $rows AS row "
            "MATCH (source:Pessoa {id: row.source_id}) "
            f"MATCH (target:{target_label} {{id: row.target_id}}) "
            f"MERGE (source)-[relationship:{relationship_type}]->(target) "
            "SET relationship += row.properties",
            rows=rows,
        ).consume()


def sync_neo4j(collections: dict[str, list[dict[str, Any]]]) -> None:
    """Upsert seed nodes and relationships in Neo4j."""
    graph_data = build_graph_data(collections, load_relationships())
    with get_neo4j_session() as session:
        session.execute_write(_write_graph, graph_data)
    print(
        "Neo4j: "
        f"{len(graph_data['people'])} pessoas, "
        f"{len(graph_data['organizations'])} organizações, "
        f"{len(graph_data['skills'])} habilidades e relacionamentos sincronizados"
    )


def main() -> None:
    """Import the seed data and synchronize unread notification counters."""
    collections = load_collections()
    hash_seed_passwords(collections)
    database = get_mongo_database()
    import_collections(database, collections)
    create_indexes(database)
    sync_unread_notification_counts(database, get_redis_client(), collections)
    sync_neo4j(collections)


if __name__ == "__main__":
    main()
