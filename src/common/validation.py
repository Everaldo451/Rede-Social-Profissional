"""Helpers genéricos de validação e normalização sem um DTO específico.

As validações específicas dos DTOs ficam junto aos próprios modelos.
"""

from datetime import date, datetime

from common.errors import InvalidDataError


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


def clean_optional_text(value, label: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    return clean_text(value, label, max_length=max_length, required=False)


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


def check_date_order(start, end, start_label: str, end_label: str) -> None:
    if start and end and end < start:
        raise InvalidDataError(
            f"A {end_label} não pode ser anterior à {start_label}."
        )


def normalize_key(value) -> str:
    """Chave de comparação/busca: sem espaços extras e sem diferença de maiúsculas."""
    return " ".join(str(value or "").split()).casefold()


def require_choice(value, choices, label: str) -> str:
    if value not in choices:
        raise InvalidDataError(f"Valor inválido para {label}.")
    return value


def clean_int(value, label: str, *, minimum: int, maximum: int, required: bool = False):
    if value is None or value == "":
        if required:
            raise InvalidDataError(f"O campo {label} é obrigatório.")
        return None
    if isinstance(value, bool):
        raise InvalidDataError(f"O campo {label} deve ser um número inteiro.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise InvalidDataError(f"O campo {label} deve ser um número inteiro.") from None
    if not minimum <= number <= maximum:
        raise InvalidDataError(f"O campo {label} deve estar entre {minimum} e {maximum}.")
    return number
