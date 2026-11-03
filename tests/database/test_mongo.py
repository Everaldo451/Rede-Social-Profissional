from src.database.mongo import get_mongo_database


def test_mongo_connection() -> None:
    response = get_mongo_database().command("ping")

    assert response["ok"] == 1
