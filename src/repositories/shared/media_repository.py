# Armazena conteúdo binário e metadados de mídia no GridFS do MongoDB.
from io import BytesIO
from typing import Any

from bson import ObjectId
from gridfs import GridFSBucket
from gridfs.errors import GridFSError
from pymongo.errors import PyMongoError
from pymongo.database import Database

from database import get_mongo_database
from services.shared.media_errors import (
    MediaPersistenceError,
    MediaValidationError,
)


class MediaRepository:
    def __init__(self, database: Database | None = None):
        self.database = (
            database if database is not None else get_mongo_database()
        )
        self.bucket = GridFSBucket(self.database, bucket_name="midias")
        self.files = self.database["midias.files"]

    # Envia o conteúdo ao GridFS e retorna os metadados do arquivo criado.
    def create(self, data):
        try:
            media_id = ObjectId()
            self.bucket.upload_from_stream_with_id(
                media_id,
                data["filename"],
                BytesIO(data["content"]),
                metadata=data["metadata"],
            )
            file_data = self.files.find_one({"_id": media_id})
            if file_data is None:
                raise MediaPersistenceError(
                    "GridFS upload completed without a files document"
                )
            return self._file_data(file_data)
        # Traduz as falhas dos drivers para a exceção de persistência usada pela aplicação.
        except (GridFSError, PyMongoError) as error:
            raise MediaPersistenceError(
                "Could not create the media file in GridFS"
            ) from error

    # Lê os metadados e o conteúdo binário do arquivo pelo identificador.
    def get_by_id(self, media_id):
        try:
            object_id = self._object_id(media_id)
            file_data = self.files.find_one({"_id": object_id})
            if file_data is None:
                return None

            content = self.bucket.open_download_stream(object_id).read()
            return self._file_data(file_data, content=content)
        except (GridFSError, PyMongoError) as error:
            raise MediaPersistenceError(
                "Could not read the media file from GridFS"
            ) from error

    # Localiza um arquivo pelos filtros e carrega seu conteúdo completo.
    def get_one(self, filters=None):
        try:
            file_data = self.files.find_one(self._build_filter(filters))
            if file_data is None:
                return None
            return self.get_by_id(file_data["_id"])
        except (GridFSError, PyMongoError) as error:
            raise MediaPersistenceError(
                "Could not find the media file in GridFS"
            ) from error

    # Lista os metadados dos arquivos mais recentes primeiro, sem carregar seus conteúdos.
    def list(self, filters=None):
        try:
            return [
                self._file_data(file_data)
                for file_data in self.files.find(self._build_filter(filters)).sort(
                    "uploadDate", -1
                )
            ]
        except (GridFSError, PyMongoError) as error:
            raise MediaPersistenceError(
                "Could not list media files from GridFS"
            ) from error

    # Atualiza nome ou metadados do arquivo e retorna a mídia resultante.
    def update(self, media_id, data):
        try:
            object_id = self._object_id(media_id)
            updates: dict[str, Any] = {}
            if "filename" in data:
                updates["filename"] = data["filename"]
            if "metadata" in data:
                updates["metadata"] = data["metadata"]
            if not updates:
                return self.get_by_id(object_id)

            result = self.files.update_one({"_id": object_id}, {"$set": updates})
            if result.matched_count == 0:
                return None
            return self.get_by_id(object_id)
        except (GridFSError, PyMongoError) as error:
            raise MediaPersistenceError(
                "Could not update the media file in GridFS"
            ) from error

    # Exclui o arquivo e seus blocos de conteúdo por meio do GridFS.
    def delete(self, media_id):
        try:
            object_id = self._object_id(media_id)
            if self.files.find_one({"_id": object_id}, {"_id": 1}) is None:
                return False
            self.bucket.delete(object_id)
            return True
        except (GridFSError, PyMongoError) as error:
            raise MediaPersistenceError(
                "Could not delete the media file from GridFS"
            ) from error

    # Converte o identificador recebido para o formato ObjectId utilizado pelo MongoDB.
    @staticmethod
    def _object_id(media_id: str | ObjectId) -> ObjectId:
        if isinstance(media_id, ObjectId):
            return media_id
        if not ObjectId.is_valid(media_id):
            raise MediaValidationError(
                "media_id must be a valid MongoDB ObjectId"
            )
        return ObjectId(media_id)

    # Traduz filtros conhecidos para filename ou campos internos de metadata.
    @staticmethod
    def _build_filter(filters: dict[str, Any] | None) -> dict[str, Any]:
        if not filters:
            return {}

        allowed_fields = {
            "filename",
            "proprietario_tipo",
            "tipo_mime",
            "tipo",
            "visibilidade",
            "proprietario_id",
        }
        query = {}
        for field, value in filters.items():
            if field not in allowed_fields:
                raise MediaValidationError(f"Unsupported media filter: {field}")
            if field == "proprietario_id":
                if (
                    not isinstance(value, ObjectId)
                    and not ObjectId.is_valid(value)
                ):
                    raise MediaValidationError(
                        "proprietario_id filter must be a valid MongoDB ObjectId"
                    )
                if not isinstance(value, ObjectId):
                    value = ObjectId(value)
            query["filename" if field == "filename" else f"metadata.{field}"] = value
        return query

    # Monta os metadados públicos do arquivo e inclui o conteúdo quando ele foi carregado.
    @staticmethod
    def _file_data(
        file_data: dict[str, Any], content: bytes | None = None
    ) -> dict[str, Any]:
        metadata = dict(file_data.get("metadata") or {})
        if isinstance(metadata.get("proprietario_id"), ObjectId):
            metadata["proprietario_id"] = str(metadata["proprietario_id"])
        result = {
            "media_id": str(file_data["_id"]),
            "filename": file_data["filename"],
            "length": file_data["length"],
            "chunk_size": file_data["chunkSize"],
            "upload_date": file_data["uploadDate"],
            "metadata": metadata,
        }
        if content is not None:
            result["content"] = content
        return result
