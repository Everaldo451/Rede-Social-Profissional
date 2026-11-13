from collections import defaultdict

from pymongo import ASCENDING

from common.errors import InvalidDataError
from repositories.shared.mongo_utils import serialize, to_object_id


class CommentRepository:
    def __init__(self, database):
        self._comments = database["comentarios"]
        self._comments.create_index([("post_id", ASCENDING), ("criado_em", ASCENDING)])

    def create(self, data):
        post_id = to_object_id(data.get("post_id"))
        author_id = to_object_id(data.get("author_id"))
        if post_id is None or author_id is None:
            raise InvalidDataError("Identificador de publicação ou autor inválido.")
        doc = {
            "post_id": post_id,
            "autor_id": author_id,
            "texto": data["text"],
            "criado_em": data["created_at"],
            "atualizado_em": data.get("updated_at", data["created_at"]),
            "comentario_pai_id": None,
        }
        self._comments.insert_one(doc)
        return self._canonical(doc)

    @staticmethod
    def _canonical(document):
        comment = serialize(document)
        if comment is None:
            return None
        comment.update(
            {
                "post_id": str(comment.get("post_id", "")),
                "author_id": str(comment.get("autor_id", "")),
                "text": comment.get("texto", ""),
                "created_at": comment.get("criado_em"),
            }
        )
        return comment

    def list_by_post_ids(self, post_ids):
        """Comentários agrupados por publicação, do mais antigo ao mais novo."""
        grouped = defaultdict(list)
        if not post_ids:
            return grouped
        object_ids = [to_object_id(post_id) for post_id in post_ids]
        object_ids = [post_id for post_id in object_ids if post_id is not None]
        if not object_ids:
            return grouped
        cursor = self._comments.find({"post_id": {"$in": object_ids}}).sort(
            "criado_em", ASCENDING
        )
        for doc in cursor:
            comment = self._canonical(doc)
            grouped[comment["post_id"]].append(comment)
        return grouped

    def delete_by_post(self, post_id):
        object_id = to_object_id(post_id)
        if object_id is None:
            return 0
        return self._comments.delete_many({"post_id": object_id}).deleted_count
