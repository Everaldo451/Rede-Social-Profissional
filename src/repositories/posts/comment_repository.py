from collections import defaultdict

from pymongo import ASCENDING

from repositories.shared.mongo_utils import serialize


class CommentRepository:
    def __init__(self, database):
        self._comments = database["comments"]
        self._comments.create_index([("post_id", ASCENDING), ("created_at", ASCENDING)])

    def create(self, data):
        doc = dict(data)
        self._comments.insert_one(doc)
        return serialize(doc)

    def list_by_post_ids(self, post_ids):
        """Comentários agrupados por publicação, do mais antigo ao mais novo."""
        grouped = defaultdict(list)
        if not post_ids:
            return grouped
        cursor = self._comments.find({"post_id": {"$in": list(post_ids)}}).sort(
            "created_at", ASCENDING
        )
        for doc in cursor:
            comment = serialize(doc)
            grouped[comment["post_id"]].append(comment)
        return grouped

    def delete_by_post(self, post_id):
        return self._comments.delete_many({"post_id": post_id}).deleted_count
