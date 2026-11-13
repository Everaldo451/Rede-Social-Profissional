from pydantic import field_validator, model_validator

from common.choices import SKILL_LEVELS, SKILL_TYPES
from common.errors import InvalidDataError
from common.validation import clean_int, clean_optional_text, clean_text, require_choice
from dto.profile.request.profile_request_base import (
    FiltersRequest,
    MongoId,
    PaginationRequest,
    ProfileRequest,
)


class SkillRequest(ProfileRequest):
    nome: str
    categoria: str = ""
    descricao: str = ""

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "habilidade", max_length=100)

    @field_validator("categoria", mode="before")
    @classmethod
    def validate_category(cls, value):
        return clean_text(value, "categoria", max_length=100, required=False)

    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_text(value, "descrição", max_length=2000, required=False)


class UpdateSkillRequest(ProfileRequest):
    nome: str | None = None
    categoria: str | None = None
    descricao: str | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            return None
        return clean_text(value, "habilidade", max_length=100)

    @field_validator("categoria", mode="before")
    @classmethod
    def validate_category(cls, value):
        return clean_optional_text(value, "categoria", max_length=100)

    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_optional_text(value, "descrição", max_length=2000)

    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.model_fields_set:
            raise InvalidDataError("Nenhuma informação para atualizar.")
        return self


class SkillIdRequest(ProfileRequest):
    habilidade_id: MongoId


class SkillPaginationRequest(PaginationRequest):
    pass


class SkillFiltersRequest(FiltersRequest):
    pass


class UserSkillRequest(ProfileRequest):
    habilidade_id: MongoId
    tipo: str
    nivel: str
    experiencia_anos: int | None = None
    modalidade: str | None = None
    disponibilidade: str | None = None

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_skill_type(cls, value):
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")

    @field_validator("nivel", mode="before")
    @classmethod
    def validate_level(cls, value):
        if value is None:
            raise InvalidDataError("O nível de competência é obrigatório.")
        cleaned = clean_text(value, "nível de competência", max_length=50)
        return require_choice(cleaned, SKILL_LEVELS, "nível de competência")

    @field_validator("experiencia_anos", mode="before")
    @classmethod
    def validate_years_experience(cls, value):
        return clean_int(value, "anos de experiência", minimum=0, maximum=80)

    @field_validator("modalidade", "disponibilidade", mode="before")
    @classmethod
    def validate_teaching_text(cls, value, info):
        return clean_optional_text(value, info.field_name, max_length=100)

    @model_validator(mode="after")
    def validate_relationship_details(self):
        if self.tipo == "has" and self.experiencia_anos is None:
            raise InvalidDataError(
                "Informe os anos de experiência para a habilidade."
            )
        if self.tipo == "teaches" and (
            self.experiencia_anos is None
            or not self.modalidade
            or not self.disponibilidade
        ):
            raise InvalidDataError(
                "Informe experiência, modalidade e disponibilidade para ensinar."
            )
        return self


class AddUserSkillRequest(UserSkillRequest):
    usuario_id: MongoId


class UserSkillByNameRequest(ProfileRequest):
    habilidade_nome: str
    tipo: str
    nivel: str
    experiencia_anos: int | None = None
    modalidade: str | None = None
    disponibilidade: str | None = None

    @field_validator("habilidade_nome", mode="before")
    @classmethod
    def validate_skill_name(cls, value):
        return clean_text(value, "habilidade", max_length=100)

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_skill_type(cls, value):
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")

    @field_validator("nivel", mode="before")
    @classmethod
    def validate_level(cls, value):
        if value is None:
            raise InvalidDataError("O nível de competência é obrigatório.")
        cleaned = clean_text(value, "nível de competência", max_length=50)
        return require_choice(cleaned, SKILL_LEVELS, "nível de competência")

    @field_validator("experiencia_anos", mode="before")
    @classmethod
    def validate_years_experience(cls, value):
        return clean_int(value, "anos de experiência", minimum=0, maximum=80)

    @field_validator("modalidade", "disponibilidade", mode="before")
    @classmethod
    def validate_teaching_text(cls, value, info):
        return clean_optional_text(value, info.field_name, max_length=100)

    @model_validator(mode="after")
    def validate_relationship_details(self):
        if self.tipo == "has" and self.experiencia_anos is None:
            raise InvalidDataError(
                "Informe os anos de experiência para a habilidade."
            )
        if self.tipo == "teaches" and (
            self.experiencia_anos is None
            or not self.modalidade
            or not self.disponibilidade
        ):
            raise InvalidDataError(
                "Informe experiência, modalidade e disponibilidade para ensinar."
            )
        return self


class UserSkillRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    habilidade_id: MongoId
    tipo: str

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_skill_type(cls, value):
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")


class UserSkillFiltersRequest(ProfileRequest):
    usuario_id: MongoId | None = None
    habilidade_id: MongoId | None = None
    tipo: str | None = None
    nivel: str | None = None

    @field_validator("tipo", mode="before")
    @classmethod
    def validate_type(cls, value):
        if value is None:
            return None
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")

    @field_validator("nivel", mode="before")
    @classmethod
    def validate_level(cls, value):
        if value is None:
            return None
        cleaned = clean_text(value, "nível de competência", max_length=50)
        return require_choice(cleaned, SKILL_LEVELS, "nível de competência")
