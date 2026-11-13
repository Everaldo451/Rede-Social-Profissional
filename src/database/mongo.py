# Configura o cliente compartilhado e o banco de documentos MongoDB.
import os

from pymongo import MongoClient
from pymongo.database import Database


# Lê a conexão do ambiente e usa o endereço do serviço Docker como padrão.
mongo_client = MongoClient(
    os.getenv("MONGO_URI", "mongodb://mongodb:27017")
)
mongo_database = mongo_client.get_default_database(
    default=os.getenv("MONGO_DATABASE", "rede_social")
)


# Retorna a mesma instância de banco para os repositórios da aplicação.
def get_mongo_database() -> Database:
    """Return the configured MongoDB database."""
    return mongo_database
