# Formato comum de resposta enviado pelos controllers para as telas.
from typing import Any
from pydantic import BaseModel


# Indica sucesso ou falha e transporta os dados e a mensagem opcionais da operação.
class BaseResponse(BaseModel):
    status: bool
    data: Any = None
    message: str | None = None
