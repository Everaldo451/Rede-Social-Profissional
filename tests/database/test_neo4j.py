from src.database.neo4j import get_neo4j_session


def test_neo4j_connection() -> None:
    with get_neo4j_session() as session:
        record = session.run("RETURN 1 AS result").single()

    assert record is not None
    assert record["result"] == 1
