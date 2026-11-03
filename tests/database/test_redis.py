from src.database.redis import get_redis_client


def test_redis_connection() -> None:
    assert get_redis_client().ping() is True
