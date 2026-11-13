# Valida habilidades e os vínculos de possuir, desenvolver ou ensinar uma competência.
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


# Define nome, categoria e descrição aceitos no cadastro de uma habilidade.
class SkillRequest(ProfileRequest):
    nome: str
    categoria: str = ""
    descricao: str = ""

    # Normaliza o nome e verifica os limites definidos para este cadastro.
    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        return clean_text(value, "habilidade", max_length=100)

    # Normaliza a categoria e verifica o limite de tamanho.
    @field_validator("categoria", mode="before")
    @classmethod
    def validate_category(cls, value):
        return clean_text(value, "categoria", max_length=100, required=False)

    # Normaliza a descrição e limita o tamanho aceito.
    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_text(value, "descrição", max_length=2000, required=False)


# Permite atualizar parcialmente os dados de uma habilidade.
class UpdateSkillRequest(ProfileRequest):
    nome: str | None = None
    categoria: str | None = None
    descricao: str | None = None

    # Normaliza o nome e verifica os limites definidos para este cadastro.
    @field_validator("nome", mode="before")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            return None
        return clean_text(value, "habilidade", max_length=100)

    # Normaliza a categoria e verifica o limite de tamanho.
    @field_validator("categoria", mode="before")
    @classmethod
    def validate_category(cls, value):
        return clean_optional_text(value, "categoria", max_length=100)

    # Normaliza a descrição e limita o tamanho aceito.
    @field_validator("descricao", mode="before")
    @classmethod
    def validate_description(cls, value):
        return clean_optional_text(value, "descrição", max_length=2000)

    # Impede uma atualização sem nenhum campo informado.
    @model_validator(mode="after")
    def validate_non_empty(self):
        if not self.model_fields_set:
            raise InvalidDataError("Nenhuma informação para atualizar.")
        return self


# Valida o identificador MongoDB de uma habilidade.
class SkillIdRequest(ProfileRequest):
    habilidade_id: MongoId


# Aplica a paginação comum às consultas de habilidades.
class SkillPaginationRequest(PaginationRequest):
    pass


# Reutiliza o modelo de filtros opcionais para consultar habilidades.
class SkillFiltersRequest(FiltersRequest):
    pass


# Define o tipo de vínculo, o nível e os detalhes de experiência ou ensino.
class UserSkillRequest(ProfileRequest):
    habilidade_id: MongoId
    tipo: str
    nivel: str
    experiencia_anos: int | None = None
    modalidade: str | None = None
    disponibilidade: str | None = None

    # Confere se a relação é possuir, querer desenvolver ou ensinar uma habilidade.
    @field_validator("tipo", mode="before")
    @classmethod
    def validate_skill_type(cls, value):
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")

    # Valida o nível de competência entre as opções cadastradas.
    @field_validator("nivel", mode="before")
    @classmethod
    def validate_level(cls, value):
        if value is None:
            raise InvalidDataError("O nível de competência é obrigatório.")
        cleaned = clean_text(value, "nível de competência", max_length=50)
        return require_choice(cleaned, SKILL_LEVELS, "nível de competência")

    # Valida os anos de experiência dentro do intervalo de zero a oitenta.
    @field_validator("experiencia_anos", mode="before")
    @classmethod
    def validate_years_experience(cls, value):
        return clean_int(value, "anos de experiência", minimum=0, maximum=80)

    # Normaliza modalidade e disponibilidade quando esses campos são informados.
    @field_validator("modalidade", "disponibilidade", mode="before")
    @classmethod
    def validate_teaching_text(cls, value, info):
        return clean_optional_text(value, info.field_name, max_length=100)

    # Exige os detalhes complementares conforme o tipo de vínculo com a habilidade.
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


# Acrescenta o usuário aos dados da habilidade que será associada ao perfil.
class AddUserSkillRequest(UserSkillRequest):
    usuario_id: MongoId


# Recebe o nome da habilidade junto dos detalhes de sua relação com o usuário.
class UserSkillByNameRequest(ProfileRequest):
    habilidade_nome: str
    tipo: str
    nivel: str
    experiencia_anos: int | None = None
    modalidade: str | None = None
    disponibilidade: str | None = None

    # Normaliza o nome da habilidade e verifica o tamanho máximo.
    @field_validator("habilidade_nome", mode="before")
    @classmethod
    def validate_skill_name(cls, value):
        return clean_text(value, "habilidade", max_length=100)

    # Confere se a relação é possuir, querer desenvolver ou ensinar uma habilidade.
    @field_validator("tipo", mode="before")
    @classmethod
    def validate_skill_type(cls, value):
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")

    # Valida o nível de competência entre as opções cadastradas.
    @field_validator("nivel", mode="before")
    @classmethod
    def validate_level(cls, value):
        if value is None:
            raise InvalidDataError("O nível de competência é obrigatório.")
        cleaned = clean_text(value, "nível de competência", max_length=50)
        return require_choice(cleaned, SKILL_LEVELS, "nível de competência")

    # Valida os anos de experiência dentro do intervalo de zero a oitenta.
    @field_validator("experiencia_anos", mode="before")
    @classmethod
    def validate_years_experience(cls, value):
        return clean_int(value, "anos de experiência", minimum=0, maximum=80)

    # Normaliza modalidade e disponibilidade quando esses campos são informados.
    @field_validator("modalidade", "disponibilidade", mode="before")
    @classmethod
    def validate_teaching_text(cls, value, info):
        return clean_optional_text(value, info.field_name, max_length=100)

    # Exige os detalhes complementares conforme o tipo de vínculo com a habilidade.
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


# Identifica o usuário, a habilidade e o tipo de vínculo que será removido.
class UserSkillRemovalRequest(ProfileRequest):
    usuario_id: MongoId
    habilidade_id: MongoId
    tipo: str

    # Confere se a relação é possuir, querer desenvolver ou ensinar uma habilidade.
    @field_validator("tipo", mode="before")
    @classmethod
    def validate_skill_type(cls, value):
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")


# Permite buscar vínculos por usuário, habilidade, tipo e nível.
class UserSkillFiltersRequest(ProfileRequest):
    usuario_id: MongoId | None = None
    habilidade_id: MongoId | None = None
    tipo: str | None = None
    nivel: str | None = None

    # Valida o tipo de vínculo quando ele é informado como filtro.
    @field_validator("tipo", mode="before")
    @classmethod
    def validate_type(cls, value):
        if value is None:
            return None
        cleaned = clean_text(value, "tipo de competência", max_length=50)
        return require_choice(cleaned, SKILL_TYPES, "tipo de competência")

    # Valida o nível de competência entre as opções cadastradas.
    @field_validator("nivel", mode="before")
    @classmethod
    def validate_level(cls, value):
        if value is None:
            return None
        cleaned = clean_text(value, "nível de competência", max_length=50)
        return require_choice(cleaned, SKILL_LEVELS, "nível de competência")
