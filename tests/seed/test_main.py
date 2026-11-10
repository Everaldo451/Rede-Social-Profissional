"""Integration test for the seed entry point."""

from typing import Any

import bcrypt

import seed as seed_script


def test_main(seed_test_environment: Any) -> None:
    """Verify the seed entry point populated each configured database."""
    database = seed_test_environment["database"]
    collections = seed_test_environment["collections"]
    redis_client = seed_test_environment["redis_client"]

    for collection_name, documents in collections.items():
        imported_documents = list(database[collection_name].find())
        assert len(imported_documents) == len(documents)
        assert {document["_id"] for document in imported_documents} == {
            document["_id"] for document in documents
        }

    for user in collections["usuarios"]:
        imported_user = database["usuarios"].find_one({"_id": user["_id"]})
        assert imported_user is not None
        assert imported_user["senha"].startswith(("$2a$", "$2b$", "$2y$"))
        assert bcrypt.checkpw(
            b"RedeSocial@2026", imported_user["senha"].encode("ascii")
        )

    assert database["usuarios"].index_information()["email_1"]["unique"]
    assert database["curtidas"].index_information()[
        "usuario_id_1_post_id_1"
    ]["unique"]

    unread_counts = {
        user["_id"]: sum(
            notification["destinatario_id"] == user["_id"]
            and notification["lida"] is False
            for notification in collections["notificacoes"]
        )
        for user in collections["usuarios"]
    }
    assert redis_client.mget(seed_test_environment["notification_keys"]) == [
        str(unread_counts[user["_id"]]).encode("ascii")
        for user in collections["usuarios"]
    ]

    graph_node_ids = seed_test_environment["graph_node_ids"]
    with seed_script.get_neo4j_session() as session:
        nodes = list(
            session.run(
                "MATCH (node) WHERE node.id IN $ids "
                "RETURN labels(node) AS labels, node.id AS id",
                ids=graph_node_ids,
            )
        )
        relationships = list(
            session.run(
                "MATCH (source)-[relationship]->(target) "
                "WHERE source.id IN $ids OR target.id IN $ids "
                "RETURN type(relationship) AS type, "
                "properties(relationship) AS properties",
                ids=graph_node_ids,
            )
        )

    graph_data = seed_test_environment["graph_data"]
    expected_node_counts = {
        "Pessoa": len(graph_data["people"]),
        "Organizacao": len(graph_data["organizations"]),
        "Habilidade": len(graph_data["skills"]),
    }
    actual_node_counts = {
        label: sum(label in node["labels"] for node in nodes)
        for label in expected_node_counts
    }
    assert actual_node_counts == expected_node_counts
    assert {node["id"] for node in nodes} == set(graph_node_ids)

    expected_relationship_counts = {
        relationship_type: len(rows)
        for relationship_type, rows in graph_data.items()
        if relationship_type in seed_script.GRAPH_RELATIONSHIPS
    }
    actual_relationship_counts = {
        relationship_type: sum(
            relationship["type"] == relationship_type
            for relationship in relationships
        )
        for relationship_type in expected_relationship_counts
    }
    assert actual_relationship_counts == expected_relationship_counts
    for relationship in relationships:
        assert (
            set(relationship["properties"])
            == seed_script.RELATIONSHIP_PROPERTIES[relationship["type"]]
        )
