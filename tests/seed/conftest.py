"""Session-scoped setup and cleanup for seed integration tests."""

from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest
from bson import ObjectId

import seed as seed_script


def _remap_object_ids(value: Any, object_ids: dict[ObjectId, ObjectId]) -> Any:
    if isinstance(value, ObjectId):
        return object_ids.setdefault(value, ObjectId())
    if isinstance(value, list):
        return [_remap_object_ids(item, object_ids) for item in value]
    if isinstance(value, dict):
        return {
            key: _remap_object_ids(item, object_ids)
            for key, item in value.items()
        }
    return value


def _remap_relationships(
    relationships: dict[str, list[dict[str, Any]]],
    object_ids: dict[ObjectId, ObjectId],
) -> dict[str, list[dict[str, Any]]]:
    return {
        relationship_type: [
            {
                "source_id": str(object_ids[ObjectId(row["source_id"])]),
                "target_id": str(object_ids[ObjectId(row["target_id"])]),
                "properties": _remap_object_ids(row["properties"], object_ids),
            }
            for row in rows
        ]
        for relationship_type, rows in relationships.items()
    }


@pytest.fixture(scope="session")
def seed_test_environment() -> Any:
    """Run the seed once before tests and remove its data after the session."""
    configured_database = seed_script.get_mongo_database()
    if "test" not in configured_database.name.lower():
        pytest.skip(
            "Seed integration tests require a MongoDB database with 'test' in its name"
        )

    mongo_client = configured_database.client
    mongo_client.admin.command("ping")
    redis_client = seed_script.get_redis_client()
    redis_client.ping()
    session_factory = seed_script.get_neo4j_session
    with session_factory() as session:
        session.run("RETURN 1").consume()

    object_ids: dict[ObjectId, ObjectId] = {}
    collections = _remap_object_ids(
        deepcopy(seed_script.load_collections()), object_ids
    )
    relationships = _remap_relationships(
        deepcopy(seed_script.load_relationships()), object_ids
    )
    graph_data = seed_script.build_graph_data(collections, relationships)
    graph_node_ids = [
        node["id"]
        for node_group in ("people", "organizations", "skills")
        for node in graph_data[node_group]
    ]
    notification_keys = [
        f"notifications:unread:{user['_id']}"
        for user in collections["usuarios"]
    ]

    if any(redis_client.mget(notification_keys)):
        raise RuntimeError(
            "Seed test Redis keys already exist; refusing to overwrite them"
        )
    with session_factory() as session:
        existing_nodes = session.run(
            "MATCH (node) WHERE node.id IN $ids RETURN count(node) AS count",
            ids=graph_node_ids,
        ).single()
    if existing_nodes is None or existing_nodes["count"] != 0:
        raise RuntimeError(
            "Seed test Neo4j IDs already exist; refusing to overwrite them"
        )

    database_name = f"seed_integration_test_{uuid4().hex}"
    database = mongo_client[database_name]
    test_data = {
        "database": database,
        "collections": collections,
        "graph_data": graph_data,
        "graph_node_ids": graph_node_ids,
        "notification_keys": notification_keys,
        "redis_client": redis_client,
    }

    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(seed_script, "get_mongo_database", lambda: database)
            monkeypatch.setattr(seed_script, "get_redis_client", lambda: redis_client)
            monkeypatch.setattr(seed_script, "get_neo4j_session", session_factory)
            monkeypatch.setattr(seed_script, "load_collections", lambda: collections)
            monkeypatch.setattr(
                seed_script, "load_relationships", lambda: relationships
            )
            seed_script.main()

        yield test_data
    finally:
        try:
            mongo_client.drop_database(database_name)
        finally:
            try:
                redis_client.delete(*notification_keys)
            finally:
                with session_factory() as session:
                    session.run(
                        "MATCH (node) WHERE node.id IN $ids "
                        "DETACH DELETE node",
                        ids=graph_node_ids,
                    ).consume()

    if database_name in mongo_client.list_database_names():
        raise AssertionError("Seed test MongoDB database was not removed")
    if any(redis_client.mget(notification_keys)):
        raise AssertionError("Seed test Redis keys were not removed")
    with session_factory() as session:
        remaining_nodes = session.run(
            "MATCH (node) WHERE node.id IN $ids RETURN count(node) AS count",
            ids=graph_node_ids,
        ).single()
    if remaining_nodes is None or remaining_nodes["count"] != 0:
        raise AssertionError("Seed test Neo4j nodes were not removed")
