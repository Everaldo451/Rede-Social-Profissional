# Teste básico de conectividade com o Neo4j.
from src.database.neo4j import get_neo4j_session


# Executa uma operação simples para conferir a resposta do Neo4j configurado.
def test_neo4j_connection() -> None:
    with get_neo4j_session() as session:
        record = session.run("RETURN 1 AS result").single()

    assert record is not None
    assert record["result"] == 1
