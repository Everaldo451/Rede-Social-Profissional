# Configura o cliente compartilhado do Redis para sessões, presença e contadores.
import os

from redis import Redis


# Obtém host e porta do ambiente, com os valores do serviço Docker como padrão.
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)


# Disponibiliza o cliente já configurado aos repositórios.
def get_redis_client() -> Redis:
    """Return the shared Redis client."""
    return redis_client
