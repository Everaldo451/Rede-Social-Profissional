from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from common.errors import ConflictError, InvalidDataError
from common.security import verify_dummy, verify_password
from common.validation import normalize_key
from database import get_mongo_database


class UserRepository:
    def __init__(self, database=None):
        if database is None:
            database = get_mongo_database()
        self.collection = database["usuarios"]
        self.collection.create_index("email", unique=True)

    @staticmethod
    def _object_id(user_id):
        try:
            return ObjectId(str(user_id))
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _serialize(user):
        if user is None:
            return None
        return {
            key: str(value) if key == "_id" and isinstance(value, ObjectId)
            else UserRepository._serialize_value(value)
            for key, value in user.items()
        }

    @staticmethod
    def _serialize_value(value):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, list):
            return [UserRepository._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {
                key: UserRepository._serialize_value(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _mongo_value(value, key=None):
        if key and key.endswith("_id") and value is not None and not isinstance(value, ObjectId):
            return ObjectId(str(value))
        if isinstance(value, list):
            return [UserRepository._mongo_value(item) for item in value]
        if isinstance(value, dict):
            return {
                nested_key: UserRepository._mongo_value(nested_value, nested_key)
                for nested_key, nested_value in value.items()
            }
        return value

    @classmethod
    def _to_document(cls, data):
        document = {}
        for key, value in data.items():
            if key == "_id":
                continue
            if key == "password":
                raise InvalidDataError("A senha deve ser armazenada somente como hash.")
            document[key] = cls._mongo_value(value, key)

        if "nome" in document and "nome_normalizado" not in document:
            document["nome_normalizado"] = normalize_key(document["nome"])
        return document

    def create(self, data):
        now = datetime.now(timezone.utc)
        user = self._to_document(data)
        user.setdefault("nivel_carreira", "")
        user.setdefault("aceita_mentoria", False)
        user.setdefault("habilidades", [])
        user.setdefault("experiencias", [])
        user.setdefault("formacao", [])
        user.setdefault("certificacoes", [])
        user.setdefault("criado_em", now)
        user.setdefault("atualizado_em", now)
        try:
            result = self.collection.insert_one(user)
        except DuplicateKeyError:
            raise ConflictError("Este e-mail já está cadastrado.") from None
        user["_id"] = result.inserted_id
        return self._serialize(user)

    def get_by_id(self, user_id):
        object_id = self._object_id(user_id)
        if object_id is None:
            return None
        return self._serialize(self.collection.find_one({"_id": object_id}))

    def get_many_by_ids(self, user_ids):
        object_ids = {
            object_id
            for object_id in (self._object_id(user_id) for user_id in user_ids)
            if object_id is not None
        }
        if not object_ids:
            return {}
        return {
            str(user["_id"]): self._serialize(user)
            for user in self.collection.find({"_id": {"$in": list(object_ids)}})
        }

    def get_by_email(self, email):
        return self._serialize(self.collection.find_one({"email": email}))

    def authenticate(self, email, password):
        if not isinstance(email, str) or not isinstance(password, str):
            return None

        user = self.collection.find_one({"email": email})
        if user is None:
            verify_dummy(password)
            return None
        password_hash = user.get("senha")
        if not isinstance(password_hash, str):
            verify_dummy(password)
            return None
        if not verify_password(password, password_hash):
            return None
        return self._serialize(user)

    def list_all(self):
        return [self._serialize(user) for user in self.collection.find({})]

    def get_paginated(self, offset, limit, filters=None):
        cursor = self.collection.find(filters or {})
        return [
            self._serialize(user)
            for user in cursor.skip(max(int(offset), 0)).limit(max(int(limit), 0))
        ]

    def list_presence_profiles(
        self, current_user_id=None, offset=0, limit=None
    ):
        filters = {}
        if current_user_id is not None:
            object_id = self._object_id(current_user_id)
            if object_id is None:
                raise ValueError("Identificador de usuário inválido.")
            filters["_id"] = {"$ne": object_id}

        users = self.collection.find(filters, {"nome": 1}).sort(
            [("nome", 1), ("_id", 1)]
        )
        users = users.skip(max(int(offset), 0))
        if limit is not None:
            users = users.limit(max(int(limit), 0))
        return [
            {"user_id": str(user["_id"]), "name": user.get("nome") or str(user["_id"])}
            for user in users
        ]

    def count_presence_profiles(self, current_user_id=None):
        filters = {}
        if current_user_id is not None:
            object_id = self._object_id(current_user_id)
            if object_id is None:
                raise ValueError("Identificador de usuário inválido.")
            filters["_id"] = {"$ne": object_id}
        return self.collection.count_documents(filters)

    def update(self, user_id, data):
        object_id = self._object_id(user_id)
        if object_id is None:
            return None

        changes = self._to_document(data)
        if not changes:
            return self.get_by_id(user_id)
        changes["atualizado_em"] = datetime.now(timezone.utc)
        try:
            user = self.collection.find_one_and_update(
                {"_id": object_id},
                {"$set": changes},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            raise ConflictError("Este e-mail já está cadastrado.") from None
        return self._serialize(user)

    def delete(self, user_id):
        object_id = self._object_id(user_id)
        if object_id is None:
            return False
        return self.collection.delete_one({"_id": object_id}).deleted_count > 0
