# Concentra a criação e a verificação dos hashes de senha.
"""Hash e verificação de senhas com bcrypt."""

import os

import bcrypt

_dummy_hash: str | None = None


# Lê o fator de custo do bcrypt; quanto maior, mais trabalho exige cada cálculo.
def _rounds() -> int:
    return int(os.getenv("BCRYPT_ROUNDS", "12"))


# Gera um salt aleatório e devolve o hash bcrypt da senha em formato textual.
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_rounds())
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Compara a senha com o hash armazenado e trata hashes inválidos como falha.
def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def verify_dummy(password: str) -> None:
    """Gasta o mesmo tempo de uma verificação real.

    Usado quando o e-mail não existe, para que o tempo de resposta não revele
    quais e-mails estão cadastrados.
    """
    # Reutiliza um hash fictício para executar bcrypt mesmo quando o e-mail não foi encontrado.
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("senha-falsa-para-igualar-tempo")
    verify_password(password, _dummy_hash)
