# Compartilha regras de limpeza de textos, validação de datas e limites numéricos.
"""Helpers genéricos de validação e normalização sem um DTO específico.

As validações específicas dos DTOs ficam junto aos próprios modelos.
"""

from datetime import date, datetime

from common.errors import InvalidDataError


# Normaliza espaços ou quebras de linha e verifica obrigatoriedade e tamanho do texto.
def clean_text(
    value,
    label: str,
    *,
    max_length: int,
    required: bool = True,
    min_length: int = 1,
    multiline: bool = False,
) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise InvalidDataError(f"O campo {label} é inválido.")

    # A opção multilinha preserva as linhas do texto; a outra compacta os espaços.
    if multiline:
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = "\n".join(line.rstrip() for line in normalized.split("\n"))
    else:
        text = " ".join(value.split())

    if not text:
        if required:
            raise InvalidDataError(f"O campo {label} é obrigatório.")
        return ""
    if len(text) < min_length:
        raise InvalidDataError(
            f"O campo {label} deve ter no mínimo {min_length} caracteres."
        )
    if len(text) > max_length:
        raise InvalidDataError(
            f"O campo {label} deve ter no máximo {max_length} caracteres."
        )
    return text


# Mantém None quando o campo está ausente e valida o texto quando ele é informado.
def clean_optional_text(value, label: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    return clean_text(value, label, max_length=max_length, required=False)


# Aceita date, datetime ou texto ISO e rejeita datas fora do intervalo permitido.
def parse_date(value, label: str, *, required: bool = False) -> date | None:
    if value is None or value == "":
        if required:
            raise InvalidDataError(f"O campo {label} é obrigatório.")
        return None

    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = date.fromisoformat(value.strip())
        except ValueError:
            raise InvalidDataError(f"Data inválida no campo {label}.") from None
    else:
        raise InvalidDataError(f"Data inválida no campo {label}.")

    if not 1900 <= parsed.year <= 2100:
        raise InvalidDataError(f"Data inválida no campo {label}.")
    return parsed


# Verifica a ordem cronológica quando as duas datas estão disponíveis.
def check_date_order(start, end, start_label: str, end_label: str) -> None:
    if start and end and end < start:
        raise InvalidDataError(
            f"A {end_label} não pode ser anterior à {start_label}."
        )


def normalize_key(value) -> str:
    """Chave de comparação/busca: sem espaços extras e sem diferença de maiúsculas."""
    return " ".join(str(value or "").split()).casefold()


# Rejeita um valor que não pertence ao conjunto de opções permitido.
def require_choice(value, choices, label: str) -> str:
    if value not in choices:
        raise InvalidDataError(f"Valor inválido para {label}.")
    return value


# Converte a entrada para inteiro e verifica os limites, rejeitando valores booleanos.
def clean_int(value, label: str, *, minimum: int, maximum: int, required: bool = False):
    if value is None or value == "":
        if required:
            raise InvalidDataError(f"O campo {label} é obrigatório.")
        return None
    # Em Python, bool é um subtipo de int, por isso precisa ser rejeitado explicitamente.
    if isinstance(value, bool):
        raise InvalidDataError(f"O campo {label} deve ser um número inteiro.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise InvalidDataError(f"O campo {label} deve ser um número inteiro.") from None
    if not minimum <= number <= maximum:
        raise InvalidDataError(f"O campo {label} deve estar entre {minimum} e {maximum}.")
    return number
