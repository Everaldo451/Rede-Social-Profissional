# Persiste e consulta organizações no MongoDB, adaptando documentos e identificadores.
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from common.validation import normalize_key
from database import get_mongo_database


class OrganizationRepository:
    def __init__(self, database=None):
        if database is None:
            database = get_mongo_database()
        self.collection = database["organizacoes"]

    # Converte o identificador recebido para o formato ObjectId utilizado pelo MongoDB.
    @staticmethod
    def _object_id(organization_id):
        try:
            return ObjectId(str(organization_id))
        except (InvalidId, TypeError):
            return None

    # Monta os campos persistidos e normaliza os valores usados nas buscas.
    @classmethod
    def _to_document(cls, data):
        document = {}
        for key, value in data.items():
            if key == "_id":
                continue
            if key == "tipos" and value is not None and not isinstance(value, list):
                value = value if isinstance(value, list) else [value]
            document[key] = cls._mongo_value(value, key)
        if "nome" in document and "nome_normalizado" not in document:
            document["nome_normalizado"] = normalize_key(document["nome"])
        return document

    # Prepara os dados retornados pelo banco, convertendo identificadores para texto.
    @classmethod
    def _serialize(cls, organization):
        if organization is None:
            return None
        result = {
            key: cls._serialize_value(value)
            for key, value in organization.items()
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
            return [OrganizationRepository._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {
                key: OrganizationRepository._serialize_value(item)
                for key, item in value.items()
            }
        return value

    # Adapta valores e referências aninhadas aos tipos usados nos documentos do MongoDB.
    @staticmethod
    def _mongo_value(value, key=None):
        if key and key.endswith("_id") and value is not None and not isinstance(value, ObjectId):
            return ObjectId(str(value))
        if isinstance(value, list):
            return [OrganizationRepository._mongo_value(item) for item in value]
        if isinstance(value, dict):
            return {
                nested_key: OrganizationRepository._mongo_value(nested_value, nested_key)
                for nested_key, nested_value in value.items()
            }
        return value

    # Prepara o documento, registra as datas aplicáveis e devolve o cadastro serializado.
    def create(self, data):
        now = datetime.now(timezone.utc)
        organization = self._to_document(data)
        organization.setdefault("criado_em", now)
        result = self.collection.insert_one(organization)
        organization["_id"] = result.inserted_id
        return self._serialize(organization)

    # Converte o identificador e consulta o documento correspondente.
    def get_by_id(self, organization_id):
        object_id = self._object_id(organization_id)
        if object_id is None:
            return None
        return self._serialize(self.collection.find_one({"_id": object_id}))

    # Aplica filtros, deslocamento e limite à consulta de documentos.
    def get_paginated(self, offset, limit, filters=None):
        cursor = self.collection.find(filters or {})
        return [
            self._serialize(organization)
            for organization in cursor.skip(max(int(offset), 0)).limit(max(int(limit), 0))
        ]

    # Retorna todos os documentos da coleção em formato serializado.
    def list_all(self):
        return [self._serialize(item) for item in self.collection.find({})]

    # Aplica as mudanças ao documento identificado e devolve seu estado atualizado.
    def update(self, organization_id, data):
        object_id = self._object_id(organization_id)
        if object_id is None:
            return None
        changes = self._to_document(data)
        if not changes:
            return self.get_by_id(organization_id)
        organization = self.collection.find_one_and_update(
            {"_id": object_id},
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(organization)

    # Remove o documento identificado e informa se a exclusão ocorreu.
    def delete(self, organization_id):
        object_id = self._object_id(organization_id)
        if object_id is None:
            return False
        return self.collection.delete_one({"_id": object_id}).deleted_count > 0
