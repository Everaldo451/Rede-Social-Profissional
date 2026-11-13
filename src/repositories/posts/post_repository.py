from pymongo import DESCENDING

from common.errors import InvalidDataError
from repositories.shared.mongo_utils import serialize, to_object_id


class PostRepository:
    def __init__(self, database):
        self._posts = database["posts"]
        self._posts.create_index([("criado_em", DESCENDING)])
        self._posts.create_index("tags")
        self._posts.create_index("categoria")

    @staticmethod
    def _query(filters):
        query = {}
        if filters and filters.get("category"):
            query["categoria"] = filters["category"]
        if filters and filters.get("author_id"):
            author_id = to_object_id(filters["author_id"])
            if author_id is None:
                raise InvalidDataError("Identificador de autor inválido.")
            query["autor_id"] = author_id
        if filters and filters.get("tag"):
            query["tags"] = filters["tag"]
        return query

    @staticmethod
    def _canonical(document):
        post = serialize(document)
        if post is None:
            return None
        post.update(
            {
                "author_id": str(post.get("autor_id", "")),
                "text": post.get("texto", ""),
                "category": post.get("categoria", "Dica"),
                "tags": post.get("tags", []),
                "code": post.get("codigo"),
                "code_language": post.get("linguagem_codigo", "text"),
                "media": post.get("midia", []),
                "created_at": post.get("criado_em"),
                "updated_at": post.get("atualizado_em"),
            }
        )
        return post

    def create(self, data):
        author_id = to_object_id(data.get("author_id"))
        if author_id is None:
            raise InvalidDataError("Identificador de autor inválido.")
        doc = {
            "autor_id": author_id,
            "texto": data["text"],
            "categoria": data["category"],
            "tags": data["tags"],
            "codigo": data.get("code"),
            "linguagem_codigo": data.get("code_language", "text"),
            "midia": data.get("media", []),
            "criado_em": data["created_at"],
            "atualizado_em": data.get("updated_at"),
        }
        self._posts.insert_one(doc)
        return self._canonical(doc)

    def get_by_id(self, post_id):
        oid = to_object_id(post_id)
        if oid is None:
            return None
        return self._canonical(self._posts.find_one({"_id": oid}))

    def get_paginated(self, offset, limit, filters=None):
        cursor = (
            self._posts.find(self._query(filters))
            .sort("criado_em", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return [self._canonical(d) for d in cursor]

    def count(self, filters=None):
        return self._posts.count_documents(self._query(filters))

    def list_all(self):
        return [
            self._canonical(d)
            for d in self._posts.find().sort("criado_em", DESCENDING)
        ]

    def update(self, post_id, data):
        oid = to_object_id(post_id)
        if oid is None:
            return False
        fields = {
            "text": "texto",
            "category": "categoria",
            "tags": "tags",
            "code": "codigo",
            "code_language": "linguagem_codigo",
            "media": "midia",
            "updated_at": "atualizado_em",
        }
        updates = {fields[key]: value for key, value in data.items() if key in fields}
        return self._posts.update_one({"_id": oid}, {"$set": updates}).matched_count > 0

    def delete(self, post_id):
        oid = to_object_id(post_id)
        if oid is None:
            return False
        return self._posts.delete_one({"_id": oid}).deleted_count > 0
