# Normalização de e-mail reutilizável pelos contratos de entrada.
import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# Remove espaços externos, converte para minúsculas e verifica o formato do e-mail.
def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL.match(value):
        raise ValueError("Informe um e-mail válido.")
    return value
