# Teste básico de conectividade com o Redis.
from src.database.redis import get_redis_client


# Executa uma operação simples para conferir a resposta do Redis configurado.
def test_redis_connection() -> None:
    assert get_redis_client().ping() is True
