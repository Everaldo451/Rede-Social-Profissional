from typing import Literal

from pydantic import BaseModel, Field


class CreateMentorshipRequest(BaseModel):
    mentor_id: str = Field(pattern=r"^[a-fA-F0-9]{24}$")
    habilidade_id: str = Field(pattern=r"^[a-fA-F0-9]{24}$")


class MentorshipDecisionRequest(BaseModel):
    acao: Literal["aceitar", "recusar"]
