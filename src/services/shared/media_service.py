from bson import ObjectId

from services.shared.media_errors import MediaValidationError


class MediaService:
    def __init__(self, media_repository):
        self.media_repository = media_repository

    def create(self, data):
        metadata = dict(data["metadata"])
        metadata["proprietario_id"] = self._owner_object_id(
            metadata["proprietario_id"]
        )
        return self.media_repository.create({**data, "metadata": metadata})

    def get_by_id(self, media_id):
        return self.media_repository.get_by_id(media_id)

    def get_one(self, filters=None):
        return self.media_repository.get_one(self._validate_filters(filters))

    def list(self, filters=None):
        return self.media_repository.list(self._validate_filters(filters))

    def update(self, media_id, data):
        updates = dict(data)
        if "metadata" in updates:
            metadata = dict(updates["metadata"])
            metadata["proprietario_id"] = self._owner_object_id(
                metadata["proprietario_id"]
            )
            updates["metadata"] = metadata
        return self.media_repository.update(media_id, updates)

    def delete(self, media_id):
        return self.media_repository.delete(media_id)

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

    @staticmethod
    def _owner_object_id(owner_id):
        if isinstance(owner_id, ObjectId):
            return owner_id
        if not isinstance(owner_id, str) or not ObjectId.is_valid(owner_id):
            raise MediaValidationError(
                "proprietario_id must be a valid MongoDB ObjectId"
            )
        return ObjectId(owner_id)
