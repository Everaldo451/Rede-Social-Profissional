import re

from pydantic import BaseModel, field_validator

CATEGORIES = ["Dica", "Dúvida", "Projeto", "Artigo", "Vaga", "Carreira"]
CODE_LANGUAGES = [
    "python", "javascript", "typescript", "java", "csharp", "cpp", "go", "rust",
    "php", "sql", "bash", "html", "css", "json", "yaml", "text",
]
MAX_TEXT = 2000
MAX_CODE = 5000
MAX_TAGS = 5
MAX_COMMENT = 1000
_TAG = re.compile(r"^[a-z0-9][a-z0-9+#._-]{0,29}$")  # aceita c#, c++, node.js...


def normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = re.split(r"[,\s]+", value)
    tags: list[str] = []
    for raw in value:
        tag = str(raw).strip().lstrip("#").lower()
        if not tag:
            continue
        if not _TAG.match(tag):
            raise ValueError(f"Tag inválida: {raw!r}. Use letras, números e + # . _ -")
        if tag not in tags:
            tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise ValueError(f"Use no máximo {MAX_TAGS} tags.")
    return tags


class PostContent(BaseModel):
    text: str
    category: str = "Dica"
    tags: list[str] = []
    code: str | None = None
    code_language: str = "python"

    @field_validator("text")
    @classmethod
    def _text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Escreva algum texto para publicar.")
        if len(value) > MAX_TEXT:
            raise ValueError(f"O texto deve ter no máximo {MAX_TEXT} caracteres.")
        return value

    @field_validator("category")
    @classmethod
    def _category(cls, value):
        if value not in CATEGORIES:
            raise ValueError("Categoria inválida.")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, value):
        return normalize_tags(value)

    @field_validator("code")
    @classmethod
    def _code(cls, value):
        value = (value or "").strip("\n")
        if not value.strip():
            return None
        if len(value) > MAX_CODE:
            raise ValueError(f"O código deve ter no máximo {MAX_CODE} caracteres.")
        return value

    @field_validator("code_language")
    @classmethod
    def _language(cls, value):
        if value not in CODE_LANGUAGES:
            raise ValueError("Linguagem do código inválida.")
        return value


class CreatePostRequest(PostContent):
    pass


class UpdatePostRequest(PostContent):
    remove_media_ids: list[str] = []


class CreateCommentRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Escreva um comentário.")
        if len(value) > MAX_COMMENT:
            raise ValueError(f"O comentário deve ter no máximo {MAX_COMMENT} caracteres.")
        return value
