# Contratos de entrada para buscar profissionais e responder a convites de conexão.
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# Permite filtrar pelo nome e, opcionalmente, por uma habilidade.
class ProfessionalSearchRequest(BaseModel):
    nome: str = Field(default="", max_length=100)
    habilidade_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{24}$")


# Identifica o convite por UUID e limita a decisão a aceitar ou recusar.
class ConnectionDecisionRequest(BaseModel):
    solicitacao_id: UUID
    acao: Literal["aceitar", "recusar"]
