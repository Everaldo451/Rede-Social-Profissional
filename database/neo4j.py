import os

from neo4j import Driver, GraphDatabase


def _get_neo4j_auth() -> tuple[str, str] | None:
    auth = os.getenv("NEO4J_AUTH", "none").strip()
    if auth.lower() == "none":
        return None

    username, separator, password = auth.partition("/")
    if not separator or not username or not password:
        raise ValueError("NEO4J_AUTH must be 'none' or use the format username/password")

    return username, password


neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
    auth=_get_neo4j_auth(),
)


def get_neo4j_driver() -> Driver:
    """Return the shared Neo4j driver."""
    return neo4j_driver
