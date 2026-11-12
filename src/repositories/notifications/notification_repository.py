from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from database.mongo import get_mongo_database
from database.redis import get_redis_client


class NotificationRepository:
    """Histórico das notificações no MongoDB e contador de não lidas no Redis."""

    COLLECTION = "notificacoes"
    UNREAD_KEY = "notifications:unread:{user_id}"

    def __init__(self, database=None, redis_client=None):
        self._database = database if database is not None else get_mongo_database()
        self._redis = redis_client if redis_client is not None else get_redis_client()
        self._collection = self._database[self.COLLECTION]

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _to_object_id(value) -> ObjectId | None:
        """Converte string para ObjectId. Devolve None se o valor for inválido."""
        if isinstance(value, ObjectId):
            return value
        try:
            return ObjectId(str(value))
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _serialize(document: dict | None) -> dict | None:
        """Converte os ObjectId do documento para string (padrão entre os bancos)."""
        if document is None:
            return None
        result = dict(document)
        for field in ("_id", "destinatario_id", "referencia_id"):
            if result.get(field) is not None:
                result[field] = str(result[field])
        return result

    def _unread_key(self, user_id) -> str:
        return self.UNREAD_KEY.format(user_id=str(user_id))

    def _increment_unread(self, user_id) -> None:
        # Se a chave não existe, o contador é reconstruído a partir do Mongo
        # na próxima leitura (count_unread_by_user_id), então não criamos aqui.
        key = self._unread_key(user_id)
        if self._redis.exists(key):
            self._redis.incr(key)

    def _decrement_unread(self, user_id) -> None:
        key = self._unread_key(user_id)
        if self._redis.exists(key):
            if self._redis.decr(key) < 0:
                self._redis.set(key, 0)

    # ------------------------------------------------------------------ CRUD

    def create(self, data):
        destinatario_id = self._to_object_id(data["destinatario_id"])
        if destinatario_id is None:
            raise ValueError("destinatario_id inválido")

        document = {
            "destinatario_id": destinatario_id,
            "tipo": data["tipo"],
            "titulo": data["titulo"],
            "referencia_tipo": data.get("referencia_tipo"),
            "referencia_id": self._to_object_id(data.get("referencia_id"))
            if data.get("referencia_id")
            else None,
            "lida": False,
            "criado_em": datetime.now(timezone.utc),
        }
        result = self._collection.insert_one(document)
        document["_id"] = result.inserted_id

        self._increment_unread(destinatario_id)
        return self._serialize(document)

    def get_by_id(self, notification_id):
        object_id = self._to_object_id(notification_id)
        if object_id is None:
            return None
        return self._serialize(self._collection.find_one({"_id": object_id}))

    def get_paginated(self, offset, limit, filters=None):
        query = {}
        filters = filters or {}

        if filters.get("destinatario_id") is not None:
            destinatario_id = self._to_object_id(filters["destinatario_id"])
            if destinatario_id is None:
                return []
            query["destinatario_id"] = destinatario_id
        if filters.get("lida") is not None:
            query["lida"] = filters["lida"]

        cursor = (
            self._collection.find(query)
            .sort("criado_em", -1)
            .skip(offset)
            .limit(limit)
        )
        return [self._serialize(document) for document in cursor]

    def count_unread_by_user_id(self, user_id):
        destinatario_id = self._to_object_id(user_id)
        if destinatario_id is None:
            return 0

        key = self._unread_key(destinatario_id)
        cached = self._redis.get(key)
        if cached is not None:
            return max(int(cached), 0)

        # Chave ausente: reconstrói o contador a partir do histórico no Mongo.
        total = self._collection.count_documents(
            {"destinatario_id": destinatario_id, "lida": False}
        )
        self._redis.set(key, total)
        return total

    def mark_all_as_read(self, user_id):
        destinatario_id = self._to_object_id(user_id)
        if destinatario_id is None:
            return 0

        result = self._collection.update_many(
            {"destinatario_id": destinatario_id, "lida": False},
            {"$set": {"lida": True}},
        )
        self._redis.set(self._unread_key(destinatario_id), 0)
        return result.modified_count

    def update(self, notification_id, data):
        """Atualiza o campo `lida` (marcar como lida / voltar para não lida)."""
        object_id = self._to_object_id(notification_id)
        if object_id is None:
            return None

        current = self._collection.find_one({"_id": object_id})
        if current is None:
            return None

        if "lida" in data:
            new_value = bool(data["lida"])
            # O filtro garante que o contador só muda se o estado realmente mudou.
            result = self._collection.update_one(
                {"_id": object_id, "lida": not new_value},
                {"$set": {"lida": new_value}},
            )
            if result.modified_count:
                if new_value:
                    self._decrement_unread(current["destinatario_id"])
                else:
                    self._increment_unread(current["destinatario_id"])

        return self.get_by_id(notification_id)

    def delete(self, notification_id):
        object_id = self._to_object_id(notification_id)
        if object_id is None:
            return False

        current = self._collection.find_one({"_id": object_id})
        if current is None:
            return False

        result = self._collection.delete_one({"_id": object_id})
        if result.deleted_count and not current.get("lida", False):
            self._decrement_unread(current["destinatario_id"])
        return bool(result.deleted_count)
