import re
from datetime import date

from pydantic import field_validator, model_validator

from common.choices import DEGREES
from common.errors import InvalidDataError
from common.validation import (
    check_date_order,
    clean_optional_text,
    clean_text,
    parse_date,
    require_choice,
)
from dto.profile.request.profile_request_base import (
    MongoId,
    PaginationRequest,
    ProfileRequest,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72


def _validate_email(value: str) -> str:
    email = clean_text(value, "e-mail", max_length=254).lower()
    if not EMAIL_PATTERN.match(email):
        raise InvalidDataError("Informe um e-mail válido.")
    return email


def _validate_password(value: str) -> str:
    if not isinstance(value, str) or len(value) < MIN_PASSWORD_LENGTH:
        raise InvalidDataError(
            f"A senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres."
        )
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise InvalidDataError("A senha é muito longa (máximo de 72 caracteres).")
    return value


class RegisterRequest(ProfileRequest):
    nome: str
    email: str
    senha: str

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "nome", max_length=100, min_length=2)

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):
        return _validate_email(value)

    @field_validator("senha", mode="before")
    @classmethod
    def validate_password(cls, value):
        return _validate_password(value)


class UserIdRequest(ProfileRequest):
    usuario_id: MongoId


class UserProfileRequest(UserIdRequest):
    visualizador_id: MongoId | None = None


class UserPaginationRequest(PaginationRequest):
    pass


class UpdateProfileRequest(ProfileRequest):
    """Atualização parcial: só os campos enviados são alterados."""

    nome: str | None = None
    headline: str | None = None
    resumo: str | None = None
    localizacao: str | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "nome", max_length=100, min_length=2)

    @field_validator("headline", mode="before")
    @classmethod
    def validate_headline(cls, value):
        return clean_text(
            value, "título profissional", max_length=120, required=False
        )

    @field_validator("resumo", mode="before")
    @classmethod
    def validate_summary(cls, value):
        return clean_text(
            value,
            "resumo profissional",
            max_length=2000,
            required=False,
            multiline=True,
        )

    @field_validator("localizacao", mode="before")
    @classmethod
    def validate_location(cls, value):
        return clean_text(value, "localização", max_length=100, required=False)

    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.model_fields_set:
            raise InvalidDataError("Nenhuma informação para atualizar.")
        return self


class ExperienceRequest(ProfileRequest):
    cargo: str
    organizacao_nome: str | None = None
    organizacao_id: MongoId | None = None
    data_inicio: date
    data_fim: date | None = None
    descricao: str | None = None

    @field_validator("cargo", mode="before")
    @classmethod
    def validate_title(cls, value):
        return clean_text(value, "cargo", max_length=120)

    @field_validator("organizacao_nome", mode="before")
    @classmethod
    def validate_organization_name(cls, value):
        return clean_optional_text(value, "organização", max_length=200)

    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_optional_text(value, "descrição", max_length=2000)

    @field_validator("data_inicio", mode="before")
    @classmethod
    def validate_start_date(cls, value):
        return parse_date(value, "data de início", required=True)

    @field_validator("data_fim", mode="before")
    @classmethod
    def validate_end_date(cls, value):
        return parse_date(value, "data de término")

    @model_validator(mode="after")
    def validate_experience(self):
        if not self.organizacao_id and not self.organizacao_nome:
            raise InvalidDataError("Informe a organização ou instituição.")
        check_date_order(
            self.data_inicio, self.data_fim, "data de início", "data de término"
        )
        return self


class ExperienceRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    organizacao_id: MongoId
    cargo: str
    data_inicio: date

    @field_validator("cargo", mode="before")
    @classmethod
    def validate_title(cls, value):
        return clean_text(value, "cargo", max_length=120)

    @field_validator("data_inicio", mode="before")
    @classmethod
    def validate_start_date(cls, value):
        return parse_date(value, "data de início", required=True)


class EducationRequest(ProfileRequest):
    curso: str
    instituicao_nome: str | None = None
    instituicao_id: MongoId | None = None
    grau: str
    data_inicio: date | None = None
    data_fim: date | None = None

    @field_validator("curso", mode="before")
    @classmethod
    def validate_course(cls, value):
        return clean_text(value, "curso", max_length=200)

    @field_validator("instituicao_nome", mode="before")
    @classmethod
    def validate_institution(cls, value):
        return clean_optional_text(value, "instituição", max_length=200)

    @field_validator("grau", mode="before")
    @classmethod
    def validate_degree(cls, value):
        cleaned = clean_text(value, "grau de formação", max_length=50)
        return require_choice(cleaned, DEGREES, "grau de formação")

    @field_validator("data_inicio", mode="before")
    @classmethod
    def validate_start_date(cls, value):
        return parse_date(value, "data de início")

    @field_validator("data_fim", mode="before")
    @classmethod
    def validate_end_date(cls, value):
        return parse_date(value, "data de término")

    @model_validator(mode="after")
    def validate_education(self):
        if not self.instituicao_id and not self.instituicao_nome:
            raise InvalidDataError("Informe a instituição de ensino.")
        check_date_order(
            self.data_inicio, self.data_fim, "data de início", "data de término"
        )
        return self


class EducationRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    instituicao_id: MongoId
    curso: str
    grau: str

    @field_validator("curso", mode="before")
    @classmethod
    def validate_course(cls, value):
        return clean_text(value, "curso", max_length=200)

    @field_validator("grau", mode="before")
    @classmethod
    def validate_degree(cls, value):
        cleaned = clean_text(value, "grau de formação", max_length=50)
        return require_choice(cleaned, DEGREES, "grau de formação")


class CertificationRequest(ProfileRequest):
    nome: str
    emissor: str
    data_emissao: date | None = None
    data_validade: date | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "certificação", max_length=200)

    @field_validator("emissor", mode="before")
    @classmethod
    def validate_issuer(cls, value):
        return clean_text(value, "emissor", max_length=200)

    @field_validator("data_emissao", mode="before")
    @classmethod
    def validate_issue_date(cls, value):
        return parse_date(value, "data de emissão")

    @field_validator("data_validade", mode="before")
    @classmethod
    def validate_expiration_date(cls, value):
        return parse_date(value, "data de validade")

    @model_validator(mode="after")
    def validate_date_order(self):
        check_date_order(
            self.data_emissao,
            self.data_validade,
            "data de emissão",
            "data de validade",
        )
        return self


class MembershipRequest(ProfileRequest):
    organizacao_id: MongoId
    papel: str
    status: str
    desde: date | None = None

    @field_validator("papel", "status", mode="before")
    @classmethod
    def validate_text(cls, value, info):
        return clean_text(value, info.field_name, max_length=100)

    @field_validator("desde", mode="before")
    @classmethod
    def validate_since(cls, value):
        return parse_date(value, "data de início")


class MembershipRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    organizacao_id: MongoId
    papel: str

    @field_validator("papel", mode="before")
    @classmethod
    def validate_role(cls, value):
        return clean_text(value, "papel", max_length=100)
