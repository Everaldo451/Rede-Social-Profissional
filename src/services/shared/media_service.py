# Valida arquivos de imagem e coordena sua persistência para perfis e publicações.
from dataclasses import dataclass

from bson import ObjectId

from services.shared.media_errors import MediaValidationError

# Cada publicação aceita até quatro imagens, com limite de dez mebibytes por arquivo.
MAX_FILES = 4
MAX_FILE_SIZE = 10 * 1024 * 1024
# Confere os bytes iniciais da imagem para não depender apenas do MIME declarado.
_IMAGE_SIGNATURES = {
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/gif": lambda data: data.startswith((b"GIF87a", b"GIF89a")),
    "image/webp": lambda data: (
        len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    ),
}


# Agrupa nome, tipo MIME e conteúdo binário de um arquivo recebido.
@dataclass(frozen=True)
class MediaFile:
    filename: str
    content_type: str
    data: bytes


class MediaService:
    def __init__(self, media_repository):
        self.media_repository = media_repository

    # Converte a referência do proprietário e encaminha o arquivo ao repositório.
    def create(self, data):
        metadata = dict(data["metadata"])
        metadata["proprietario_id"] = self._owner_object_id(
            metadata["proprietario_id"]
        )
        return self.media_repository.create({**data, "metadata": metadata})

    # Valida a imagem e monta os metadados de uma foto pública de perfil.
    def create_profile_image(self, file: MediaFile, owner_id: str):
        self._validate_upload(file)
        return self.create(
            {
                "filename": file.filename,
                "content": file.data,
                "metadata": {
                    "proprietario_tipo": "usuario",
                    "tipo_mime": file.content_type,
                    "tipo": "imagem_perfil",
                    "visibilidade": "publica",
                    "proprietario_id": owner_id,
                },
            }
        )

    # Consulta a mídia pelo identificador.
    def get_by_id(self, media_id):
        return self.media_repository.get_by_id(media_id)

    # Valida os filtros e consulta uma mídia correspondente.
    def get_one(self, filters=None):
        return self.media_repository.get_one(self._validate_filters(filters))

    # Valida os filtros e lista os arquivos correspondentes.
    def list(self, filters=None):
        return self.media_repository.list(self._validate_filters(filters))

    # Prepara a referência do proprietário quando os metadados são atualizados.
    def update(self, media_id, data):
        updates = dict(data)
        if "metadata" in updates:
            metadata = dict(updates["metadata"])
            metadata["proprietario_id"] = self._owner_object_id(
                metadata["proprietario_id"]
            )
            updates["metadata"] = metadata
        return self.media_repository.update(media_id, updates)

    # Delega ao repositório a remoção do arquivo de mídia.
    def delete(self, media_id):
        return self.media_repository.delete(media_id)

    # Valida o limite de imagens e armazena os arquivos associados a uma publicação.
    def store_many(self, files, owner_id, already_attached=0):
        files = list(files or ())
        if already_attached + len(files) > MAX_FILES:
            raise MediaValidationError(
                f"Uma publicação pode ter no máximo {MAX_FILES} imagens."
            )

        stored = []
        try:
            for file in files:
                self._validate_upload(file)
                media = self.create(
                    {
                        "filename": file.filename,
                        "content": file.data,
                        "metadata": {
                            "proprietario_tipo": "post",
                            "tipo_mime": file.content_type,
                            "tipo": "imagem_publicacao",
                            "visibilidade": "publica",
                            "proprietario_id": owner_id,
                        },
                    }
                )
                stored.append(
                    {
                        "id": media["media_id"],
                        "filename": media["filename"],
                        "content_type": file.content_type,
                    }
                )
        # Se um arquivo do lote falhar, remove os arquivos que este lote já havia gravado.
        except Exception:
            self.delete_many([item["id"] for item in stored])
            raise
        return stored

    # Remove cada mídia da lista de identificadores recebida.
    def delete_many(self, media_ids):
        return [self.delete(media_id) for media_id in media_ids]

    # Verifica tipo do objeto, conteúdo não vazio, tamanho e assinatura binária da imagem.
    @staticmethod
    def _validate_upload(file):
        if not isinstance(file, MediaFile):
            raise MediaValidationError("Arquivo de imagem inválido.")
        if not file.filename or not isinstance(file.data, bytes) or not file.data:
            raise MediaValidationError("O arquivo de imagem está vazio.")
        if len(file.data) > MAX_FILE_SIZE:
            raise MediaValidationError("Cada imagem deve ter no máximo 10 MB.")
        signature = _IMAGE_SIGNATURES.get(file.content_type)
        if signature is None or not signature(file.data):
            raise MediaValidationError(
                "O conteúdo do arquivo não corresponde a uma imagem permitida."
            )

    # Aceita apenas os filtros conhecidos e converte o identificador do proprietário.
    @staticmethod
    def _validate_filters(filters):
        if filters is None:
            return None

        allowed_fields = {
            "filename",
            "proprietario_tipo",
            "tipo_mime",
            "tipo",
            "visibilidade",
            "proprietario_id",
        }
        unsupported_fields = set(filters) - allowed_fields
        if unsupported_fields:
            names = ", ".join(sorted(unsupported_fields))
            raise MediaValidationError(f"Unsupported media filter(s): {names}")

        validated_filters = dict(filters)
        if "proprietario_id" in validated_filters:
            validated_filters["proprietario_id"] = MediaService._owner_object_id(
                validated_filters["proprietario_id"]
            )
        return validated_filters

    # Aceita ObjectId ou texto hexadecimal válido para identificar o proprietário.
    @staticmethod
    def _owner_object_id(owner_id):
        if isinstance(owner_id, ObjectId):
            return owner_id
        if not isinstance(owner_id, str) or not ObjectId.is_valid(owner_id):
            raise MediaValidationError(
                "proprietario_id must be a valid MongoDB ObjectId"
            )
        return ObjectId(owner_id)
