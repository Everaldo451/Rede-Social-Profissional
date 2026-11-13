# Reúne modelos compartilhados para operações com organizações, habilidades e interações.
from pydantic import BaseModel, Field, field_validator


# Define os campos de nome, descrição e site com limites de tamanho.
class OrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    website: str = Field(default="", max_length=250)

    # Remove espaços nas extremidades do nome recebido.
    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        return value.strip()


# Representa uma habilidade por nome e categoria.
class SkillRequest(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    category: str = Field(default="Tecnologia", max_length=60)

    # Remove os espaços externos dos textos submetidos ao validador.
    @field_validator("name", "category")
    @classmethod
    def clean(cls, value):
        return value.strip()


# Define usuário, título, descrição e lista limitada de habilidades da mentoria.
class MentorshipRequest(BaseModel):
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=1000)
    skills: list[str] = Field(default_factory=list, max_length=10)


# Define destinatário, conteúdo e tipo permitido de uma notificação.
class NotificationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    kind: str = Field(default="info", pattern="^(info|connection|comment|like|system)$")


# Restringe o estado da conexão e limita o tamanho da observação.
class ConnectionRequest(BaseModel):
    status: str = Field(default="pending", pattern="^(pending|accepted|rejected)$")
    note: str = Field(default="", max_length=300)
