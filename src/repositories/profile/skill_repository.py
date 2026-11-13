# Persiste e consulta habilidades no MongoDB, adaptando documentos e identificadores.
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from common.validation import normalize_key
from database import get_mongo_database


class SkillRepository:
    def __init__(self, database=None):
        if database is None:
            database = get_mongo_database()
        self.collection = database["habilidades"]

    # Converte o identificador recebido para o formato ObjectId utilizado pelo MongoDB.
    @staticmethod
    def _object_id(skill_id):
        try:
            return ObjectId(str(skill_id))
        except (InvalidId, TypeError):
            return None

    # Monta os campos persistidos e normaliza os valores usados nas buscas.
    @classmethod
    def _to_document(cls, data):
        document = {
            key: cls._mongo_value(value, key)
            for key, value in data.items()
            if key != "_id"
        }
        if "nome" in document and "nome_normalizado" not in document:
            document["nome_normalizado"] = normalize_key(document["nome"])
        return document

    # Prepara os dados retornados pelo banco, convertendo identificadores para texto.
    @classmethod
    def _serialize(cls, skill):
        if skill is None:
            return None
        result = {
            key: cls._serialize_value(value)
            for key, value in skill.items()
        }
        if isinstance(result.get("_id"), ObjectId):
            result["_id"] = str(result["_id"])
        return result

    # Converte identificadores também dentro de listas e dicionários aninhados.
    @staticmethod
    def _serialize_value(value):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, list):
            return [SkillRepository._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {
                key: SkillRepository._serialize_value(item)
                for key, item in value.items()
            }
        return value

    # Adapta valores e referências aninhadas aos tipos usados nos documentos do MongoDB.
    @staticmethod
    def _mongo_value(value, key=None):
        if key and key.endswith("_id") and value is not None and not isinstance(value, ObjectId):
            return ObjectId(str(value))
        if isinstance(value, list):
            return [SkillRepository._mongo_value(item) for item in value]
        if isinstance(value, dict):
            return {
                nested_key: SkillRepository._mongo_value(nested_value, nested_key)
                for nested_key, nested_value in value.items()
            }
        return value

    # Prepara o documento, registra as datas aplicáveis e devolve o cadastro serializado.
    def create(self, data):
        now = datetime.now(timezone.utc)
        skill = self._to_document(data)
        skill.setdefault("criado_em", now)
        skill.setdefault("atualizado_em", now)
        result = self.collection.insert_one(skill)
        skill["_id"] = result.inserted_id
        return self._serialize(skill)

    # Converte o identificador e consulta o documento correspondente.
    def get_by_id(self, skill_id):
        object_id = self._object_id(skill_id)
        if object_id is None:
            return None
        return self._serialize(self.collection.find_one({"_id": object_id}))

    # Consulta um documento que corresponda aos filtros informados.
    def get_one(self, filters=None):
        return self._serialize(self.collection.find_one(filters or {}))

    # Aplica filtros, deslocamento e limite à consulta de documentos.
    def get_paginated(self, offset, limit, filters=None):
        cursor = self.collection.find(filters or {})
        return [
            self._serialize(skill)
            for skill in cursor.skip(max(int(offset), 0)).limit(max(int(limit), 0))
        ]

    # Aplica as mudanças ao documento identificado e devolve seu estado atualizado.
    def update(self, skill_id, data):
        object_id = self._object_id(skill_id)
        if object_id is None:
            return None
        changes = self._to_document(data)
        if not changes:
            return self.get_by_id(skill_id)
        changes["atualizado_em"] = datetime.now(timezone.utc)
        skill = self.collection.find_one_and_update(
            {"_id": object_id},
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(skill)

    # Remove o documento identificado e informa se a exclusão ocorreu.
    def delete(self, skill_id):
        object_id = self._object_id(skill_id)
        if object_id is None:
            return False
        return self.collection.delete_one({"_id": object_id}).deleted_count > 0
