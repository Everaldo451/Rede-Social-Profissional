# Modelos básicos reutilizados pelos DTOs de perfil, paginação e filtros.
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.validation import clean_int

MongoId = Annotated[str, Field(pattern=r"^[a-fA-F0-9]{24}$")]


# Define a configuração compartilhada das requisições de perfil.
class ProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Recebe posição, tamanho de página e filtros para consultas paginadas.
class PaginationRequest(ProfileRequest):
    offset: int = 0
    limit: int = 20
    filters: dict[str, Any] | None = None

    # Aceita somente uma posição inicial inteira dentro do intervalo permitido.
    @field_validator("offset", mode="before")
    @classmethod
    def validate_offset(cls, value):
        return clean_int(value, "offset", minimum=0, maximum=2_147_483_647, required=True)

    # Limita a quantidade de registros solicitada em cada página.
    @field_validator("limit", mode="before")
    @classmethod
    def validate_limit(cls, value):
        return clean_int(value, "limit", minimum=1, maximum=100, required=True)


# Encapsula os filtros opcionais de uma consulta.
class FiltersRequest(ProfileRequest):
    filters: dict[str, Any] | None = None
