# DTOs que limitam os dados aceitos na solicitação e na resposta de uma mentoria.
from typing import Literal

from pydantic import BaseModel, Field


# Exige os identificadores do mentor e da habilidade no formato hexadecimal do MongoDB.
class CreateMentorshipRequest(BaseModel):
    mentor_id: str = Field(pattern=r"^[a-fA-F0-9]{24}$")
    habilidade_id: str = Field(pattern=r"^[a-fA-F0-9]{24}$")


# Restringe a resposta da mentoria às ações aceitar ou recusar.
class MentorshipDecisionRequest(BaseModel):
    acao: Literal["aceitar", "recusar"]
