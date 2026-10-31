import os

from neo4j import Driver, GraphDatabase, Session


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
neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")


def get_neo4j_session() -> Session:
    """Return a session for the configured Neo4j database."""
    return neo4j_driver.session(database=neo4j_database)
