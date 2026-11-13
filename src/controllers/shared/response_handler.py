# Padroniza o resultado e as falhas esperadas das operações de publicações.
from pydantic import ValidationError

from common.errors import AppError
from dto.shared.response.base_response import BaseResponse


def run(action) -> BaseResponse:
    """Executa a ação e converte erros esperados em BaseResponse(status=False)."""
    try:
        return BaseResponse(status=True, data=action())
    except AppError as exc:
        return BaseResponse(status=False, message=str(exc))
    except ValidationError as exc:
        # Extrai a primeira mensagem de validação para exibi-la sem o prefixo técnico do Pydantic.
        message = exc.errors()[0]["msg"].removeprefix("Value error, ")
        return BaseResponse(status=False, message=message)
