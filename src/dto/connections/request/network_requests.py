from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProfessionalSearchRequest(BaseModel):
    nome: str = Field(default="", max_length=100)
    habilidade_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{24}$")


class ConnectionDecisionRequest(BaseModel):
    solicitacao_id: UUID
    acao: Literal["aceitar", "recusar"]
