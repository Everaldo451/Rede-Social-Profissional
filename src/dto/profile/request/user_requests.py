# Modelos de entrada para conta, perfil, experiências, formação, certificações e vínculos.
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


# Normaliza o e-mail em minúsculas e confere seu formato.
def _validate_email(value: str) -> str:
    email = clean_text(value, "e-mail", max_length=254).lower()
    if not EMAIL_PATTERN.match(email):
        raise InvalidDataError("Informe um e-mail válido.")
    return email


# Verifica o comprimento mínimo da senha e o limite de 72 bytes do bcrypt.
def _validate_password(value: str) -> str:
    if not isinstance(value, str) or len(value) < MIN_PASSWORD_LENGTH:
        raise InvalidDataError(
            f"A senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres."
        )
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise InvalidDataError("A senha é muito longa (máximo de 72 caracteres).")
    return value


# Define nome, e-mail e senha exigidos para criar uma conta.
class RegisterRequest(ProfileRequest):
    nome: str
    email: str
    senha: str

    # Normaliza o nome e verifica os limites definidos para este cadastro.
    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "nome", max_length=100, min_length=2)

    # Reutiliza a validação de formato e a normalização do e-mail.
    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):
        return _validate_email(value)

    # Aplica os limites de senha definidos para o cadastro.
    @field_validator("senha", mode="before")
    @classmethod
    def validate_password(cls, value):
        return _validate_password(value)


# Valida o identificador MongoDB de um usuário.
class UserIdRequest(ProfileRequest):
    usuario_id: MongoId


# Acrescenta a identificação opcional de quem está consultando o perfil.
class UserProfileRequest(UserIdRequest):
    visualizador_id: MongoId | None = None


# Reutiliza a validação comum de páginas na consulta de usuários.
class UserPaginationRequest(PaginationRequest):
    pass


# Aceita os campos editáveis do perfil sem exigir o envio de todos eles.
class UpdateProfileRequest(ProfileRequest):
    """Atualização parcial: só os campos enviados são alterados."""

    nome: str | None = None
    headline: str | None = None
    resumo: str | None = None
    localizacao: str | None = None

    # Normaliza o nome e verifica os limites definidos para este cadastro.
    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "nome", max_length=100, min_length=2)

    # Normaliza o título profissional e limita seu tamanho.
    @field_validator("headline", mode="before")
    @classmethod
    def validate_headline(cls, value):
        return clean_text(
            value, "título profissional", max_length=120, required=False
        )

    # Valida o resumo profissional preservando sua estrutura de parágrafos.
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

    # Normaliza a localização e verifica o tamanho máximo.
    @field_validator("localizacao", mode="before")
    @classmethod
    def validate_location(cls, value):
        return clean_text(value, "localização", max_length=100, required=False)

    # Impede uma atualização sem nenhum campo informado.
    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.model_fields_set:
            raise InvalidDataError("Nenhuma informação para atualizar.")
        return self


# Representa cargo, organização, período e descrição de uma experiência profissional.
class ExperienceRequest(ProfileRequest):
    cargo: str
    organizacao_nome: str | None = None
    organizacao_id: MongoId | None = None
    data_inicio: date
    data_fim: date | None = None
    descricao: str | None = None

    # Normaliza o cargo informado e verifica o limite de tamanho.
    @field_validator("cargo", mode="before")
    @classmethod
    def validate_title(cls, value):
        return clean_text(value, "cargo", max_length=120)

    # Normaliza o nome opcional da organização.
    @field_validator("organizacao_nome", mode="before")
    @classmethod
    def validate_organization_name(cls, value):
        return clean_optional_text(value, "organização", max_length=200)

    # Normaliza a descrição e limita o tamanho aceito.
    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_optional_text(value, "descrição", max_length=2000)

    # Converte a data de início para o tipo date e aplica a validação de datas.
    @field_validator("data_inicio", mode="before")
    @classmethod
    def validate_start_date(cls, value):
        return parse_date(value, "data de início", required=True)

    # Converte a data de término, permitindo que ela não seja informada.
    @field_validator("data_fim", mode="before")
    @classmethod
    def validate_end_date(cls, value):
        return parse_date(value, "data de término")

    # Exige uma organização e impede que o término anteceda o início da experiência.
    @model_validator(mode="after")
    def validate_experience(self):
        if not self.organizacao_id and not self.organizacao_nome:
            raise InvalidDataError("Informe a organização ou instituição.")
        check_date_order(
            self.data_inicio, self.data_fim, "data de início", "data de término"
        )
        return self


# Reúne os campos que distinguem a experiência profissional a remover.
class ExperienceRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    organizacao_id: MongoId
    cargo: str
    data_inicio: date

    # Normaliza o cargo informado e verifica o limite de tamanho.
    @field_validator("cargo", mode="before")
    @classmethod
    def validate_title(cls, value):
        return clean_text(value, "cargo", max_length=120)

    # Converte a data de início para o tipo date e aplica a validação de datas.
    @field_validator("data_inicio", mode="before")
    @classmethod
    def validate_start_date(cls, value):
        return parse_date(value, "data de início", required=True)


# Representa curso, instituição, grau e período de formação.
class EducationRequest(ProfileRequest):
    curso: str
    instituicao_nome: str | None = None
    instituicao_id: MongoId | None = None
    grau: str
    data_inicio: date | None = None
    data_fim: date | None = None

    # Normaliza o nome do curso e verifica o tamanho máximo.
    @field_validator("curso", mode="before")
    @classmethod
    def validate_course(cls, value):
        return clean_text(value, "curso", max_length=200)

    # Normaliza o nome opcional da instituição de ensino.
    @field_validator("instituicao_nome", mode="before")
    @classmethod
    def validate_institution(cls, value):
        return clean_optional_text(value, "instituição", max_length=200)

    # Aceita somente um grau de formação presente nas opções do sistema.
    @field_validator("grau", mode="before")
    @classmethod
    def validate_degree(cls, value):
        cleaned = clean_text(value, "grau de formação", max_length=50)
        return require_choice(cleaned, DEGREES, "grau de formação")

    # Converte a data de início para o tipo date e aplica a validação de datas.
    @field_validator("data_inicio", mode="before")
    @classmethod
    def validate_start_date(cls, value):
        return parse_date(value, "data de início")

    # Converte a data de término, permitindo que ela não seja informada.
    @field_validator("data_fim", mode="before")
    @classmethod
    def validate_end_date(cls, value):
        return parse_date(value, "data de término")

    # Exige uma instituição e verifica a ordem das datas da formação.
    @model_validator(mode="after")
    def validate_education(self):
        if not self.instituicao_id and not self.instituicao_nome:
            raise InvalidDataError("Informe a instituição de ensino.")
        check_date_order(
            self.data_inicio, self.data_fim, "data de início", "data de término"
        )
        return self


# Identifica uma formação pelo usuário, instituição, curso e grau.
class EducationRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    instituicao_id: MongoId
    curso: str
    grau: str

    # Normaliza o nome do curso e verifica o tamanho máximo.
    @field_validator("curso", mode="before")
    @classmethod
    def validate_course(cls, value):
        return clean_text(value, "curso", max_length=200)

    # Aceita somente um grau de formação presente nas opções do sistema.
    @field_validator("grau", mode="before")
    @classmethod
    def validate_degree(cls, value):
        cleaned = clean_text(value, "grau de formação", max_length=50)
        return require_choice(cleaned, DEGREES, "grau de formação")


# Representa a certificação, seu emissor e suas datas opcionais.
class CertificationRequest(ProfileRequest):
    nome: str
    emissor: str
    data_emissao: date | None = None
    data_validade: date | None = None

    # Normaliza o nome e verifica os limites definidos para este cadastro.
    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "certificação", max_length=200)

    # Normaliza o nome do emissor da certificação.
    @field_validator("emissor", mode="before")
    @classmethod
    def validate_issuer(cls, value):
        return clean_text(value, "emissor", max_length=200)

    # Converte a data opcional de emissão da certificação.
    @field_validator("data_emissao", mode="before")
    @classmethod
    def validate_issue_date(cls, value):
        return parse_date(value, "data de emissão")

    # Converte a data opcional de validade da certificação.
    @field_validator("data_validade", mode="before")
    @classmethod
    def validate_expiration_date(cls, value):
        return parse_date(value, "data de validade")

    # Impede que a validade da certificação seja anterior à emissão.
    @model_validator(mode="after")
    def validate_date_order(self):
        check_date_order(
            self.data_emissao,
            self.data_validade,
            "data de emissão",
            "data de validade",
        )
        return self


# Descreve papel, situação e início do vínculo com uma organização.
class MembershipRequest(ProfileRequest):
    organizacao_id: MongoId
    papel: str
    status: str
    desde: date | None = None

    # Normaliza o campo textual indicado pelo validador.
    @field_validator("papel", "status", mode="before")
    @classmethod
    def validate_text(cls, value, info):
        return clean_text(value, info.field_name, max_length=100)

    # Converte a data opcional de início do vínculo com a organização.
    @field_validator("desde", mode="before")
    @classmethod
    def validate_since(cls, value):
        return parse_date(value, "data de início")


# Identifica o vínculo com a organização que será removido.
class MembershipRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    organizacao_id: MongoId
    papel: str

    # Normaliza o papel exercido na organização.
    @field_validator("papel", mode="before")
    @classmethod
    def validate_role(cls, value):
        return clean_text(value, "papel", max_length=100)
