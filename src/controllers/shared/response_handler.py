from pydantic import ValidationError

from dto.shared.response.base_response import BaseResponse
from services.shared.errors import AppError


def run(action) -> BaseResponse:
    """Executa a ação e converte erros esperados em BaseResponse(status=False)."""
    try:
        return BaseResponse(status=True, data=action())
    except AppError as exc:
        return BaseResponse(status=False, message=str(exc))
    except ValidationError as exc:
        message = exc.errors()[0]["msg"].removeprefix("Value error, ")
        return BaseResponse(status=False, message=message)
