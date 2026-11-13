# Teste básico de conectividade com o MongoDB.
from src.database.mongo import get_mongo_database


# Executa uma operação simples para conferir a resposta do MongoDB configurado.
def test_mongo_connection() -> None:
    response = get_mongo_database().command("ping")

    assert response["ok"] == 1
