from pymongo import DESCENDING

from repositories.shared.mongo_utils import serialize, to_object_id


class PostRepository:
    def __init__(self, database):
        self._posts = database["posts"]
        self._posts.create_index([("created_at", DESCENDING)])
        self._posts.create_index("tags")
        self._posts.create_index("category")

    @staticmethod
    def _query(filters):
        query = {}
        for key in ("category", "author_id"):
            if filters and filters.get(key):
                query[key] = filters[key]
        if filters and filters.get("tag"):
            query["tags"] = filters["tag"]
        return query

    def create(self, data):
        doc = dict(data)
        self._posts.insert_one(doc)
        return serialize(doc)

    def get_by_id(self, post_id):
        oid = to_object_id(post_id)
        if oid is None:
            return None
        return serialize(self._posts.find_one({"_id": oid}))

    def get_paginated(self, offset, limit, filters=None):
        cursor = (
            self._posts.find(self._query(filters))
            .sort("created_at", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return [serialize(d) for d in cursor]

    def count(self, filters=None):
        return self._posts.count_documents(self._query(filters))

    def list_all(self):
        return [serialize(d) for d in self._posts.find().sort("created_at", DESCENDING)]

    def update(self, post_id, data):
        oid = to_object_id(post_id)
        if oid is None:
            return False
        return self._posts.update_one({"_id": oid}, {"$set": data}).matched_count > 0

    def delete(self, post_id):
        oid = to_object_id(post_id)
        if oid is None:
            return False
        return self._posts.delete_one({"_id": oid}).deleted_count > 0
