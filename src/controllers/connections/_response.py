# Compartilha o tratamento de respostas dos controllers de conexões e mentorias.
from pydantic import ValidationError

from dto.shared.response.base_response import BaseResponse


# Executa a ação e converte falhas de validação ou de negócio em BaseResponse.
def run_action(action, *args):
    try:
        return BaseResponse(status=True, data=action(*args))
    except ValidationError:
        return BaseResponse(status=False, message="Verifique os dados informados.")
    except ValueError as error:
        return BaseResponse(status=False, message=str(error))
