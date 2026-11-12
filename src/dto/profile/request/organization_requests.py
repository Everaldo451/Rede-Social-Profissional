from pydantic import field_validator, model_validator

from common.choices import ORGANIZATION_TYPES
from common.errors import InvalidDataError
from common.validation import clean_optional_text, clean_text, require_choice
from dto.profile.request.profile_request_base import (
    MongoId,
    PaginationRequest,
    ProfileRequest,
)


class OrganizationRequest(ProfileRequest):
    nome: str
    tipo: str
    setor: str | None = None
    descricao: str | None = None
    site: str | None = None
    localizacao: str | None = None
    sigla: str | None = None
    cidade: str | None = None
    estado: str | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "organização", max_length=200)

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_type(cls, value):
        cleaned = clean_text(value, "tipo de organização", max_length=50)
        return require_choice(cleaned, ORGANIZATION_TYPES, "tipo de organização")

    @field_validator(
        "setor", "site", "localizacao", "sigla", "cidade", "estado", mode="before"
    )
    @classmethod
    def validate_optional_fields(cls, value, info):
        return clean_optional_text(value, info.field_name, max_length=500)

    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_optional_text(value, "descrição", max_length=2000)


class UpdateOrganizationRequest(ProfileRequest):
    nome: str | None = None
    tipo: str | None = None
    setor: str | None = None
    descricao: str | None = None
    site: str | None = None
    localizacao: str | None = None
    sigla: str | None = None
    cidade: str | None = None
    estado: str | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            return None
        return clean_text(value, "organização", max_length=200)

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_type(cls, value):
        if value is None:
            return None
        cleaned = clean_text(value, "tipo de organização", max_length=50)
        return require_choice(cleaned, ORGANIZATION_TYPES, "tipo de organização")

    @field_validator(
        "setor", "site", "localizacao", "sigla", "cidade", "estado", mode="before"
    )
    @classmethod
    def validate_optional_fields(cls, value, info):
        return clean_optional_text(value, info.field_name, max_length=500)

    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_optional_text(value, "descrição", max_length=2000)

    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.model_fields_set:
            raise InvalidDataError("Nenhuma informação para atualizar.")
        return self


class OrganizationIdRequest(ProfileRequest):
    organizacao_id: MongoId


class OrganizationCreatorRequest(ProfileRequest):
    usuario_id: MongoId


class OrganizationPaginationRequest(PaginationRequest):
    pass
