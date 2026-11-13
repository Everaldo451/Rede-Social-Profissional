# Contratos de entrada para arquivos de imagem, seus metadados e filtros de consulta.
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Define o proprietário da imagem, o tipo de uso, o MIME e a visibilidade.
class MediaMetadataRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    proprietario_tipo: Literal["usuario", "post"]
    tipo_mime: str = Field(pattern=r"^image/[A-Za-z0-9.+-]+$")
    tipo: Literal["imagem_perfil", "imagem_publicacao"]
    visibilidade: str = Field(min_length=1)
    proprietario_id: str

    # Confere se o identificador do proprietário pode ser convertido em ObjectId.
    @field_validator("proprietario_id")
    @classmethod
    def validate_proprietario_id(cls, value: str) -> str:
        if not ObjectId.is_valid(value):
            raise ValueError("proprietario_id must be a valid MongoDB ObjectId")
        return value

    # Exige coerência entre o proprietário e o uso como imagem de perfil ou publicação.
    @model_validator(mode="after")
    def validate_owner_media_type(self) -> "MediaMetadataRequest":
        expected_type = {
            "usuario": "imagem_perfil",
            "post": "imagem_publicacao",
        }[self.proprietario_tipo]
        if self.tipo != expected_type:
            raise ValueError(
                f"{self.proprietario_tipo} media must use tipo={expected_type}"
            )
        return self


# Exige nome do arquivo, conteúdo não vazio e metadados válidos.
class MediaCreateRequest(BaseModel):
    filename: str = Field(min_length=1)
    content: bytes = Field(min_length=1)
    metadata: MediaMetadataRequest


# Valida o identificador do arquivo de mídia.
class MediaIdRequest(BaseModel):
    media_id: str = Field(min_length=1)

    # Rejeita identificadores que não possuem o formato ObjectId.
    @field_validator("media_id")
    @classmethod
    def validate_media_id(cls, value: str) -> str:
        if not ObjectId.is_valid(value):
            raise ValueError("media_id must be a valid MongoDB ObjectId")
        return value


# Encapsula os filtros aceitos nas consultas de mídia.
class MediaFiltersRequest(BaseModel):
    filters: dict[str, str] | None = None

    # Rejeita filtros desconhecidos e verifica o identificador do proprietário.
    @model_validator(mode="after")
    def validate_filters(self) -> "MediaFiltersRequest":
        if self.filters is None:
            return self

        allowed_fields = {
            "filename",
            "proprietario_tipo",
            "tipo_mime",
            "tipo",
            "visibilidade",
            "proprietario_id",
        }
        unsupported_fields = set(self.filters) - allowed_fields
        if unsupported_fields:
            names = ", ".join(sorted(unsupported_fields))
            raise ValueError(f"Unsupported media filter(s): {names}")

        owner_id = self.filters.get("proprietario_id")
        if owner_id is not None and not ObjectId.is_valid(owner_id):
            raise ValueError(
                "proprietario_id filter must be a valid MongoDB ObjectId"
            )
        return self


# Permite modificar nome do arquivo, metadados ou ambos.
class MediaUpdateRequest(BaseModel):
    filename: str | None = Field(default=None, min_length=1)
    metadata: MediaMetadataRequest | None = None

    # Exige pelo menos um campo para executar a atualização da mídia.
    @model_validator(mode="after")
    def require_update_fields(self) -> "MediaUpdateRequest":
        if self.filename is None and self.metadata is None:
            raise ValueError("At least one of filename or metadata must be provided")
        return self
