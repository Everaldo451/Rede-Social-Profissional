# Configura o driver do Neo4j, usado para consultar e manter os relacionamentos do grafo.
import atexit
import os

from neo4j import Driver, GraphDatabase, Session


# Interpreta a autenticação como usuário/senha ou desativada pelo valor none.
def _get_neo4j_auth() -> tuple[str, str] | None:
    auth = os.getenv("NEO4J_AUTH", "neo4j/neo4jdev123").strip()
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
# Fecha o driver quando o processo Python termina.
atexit.register(neo4j_driver.close)
neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")


# Abre uma sessão no banco configurado para a próxima operação no grafo.
def get_neo4j_session() -> Session:
    """Return a session for the configured Neo4j database."""
    return neo4j_driver.session(database=neo4j_database)
