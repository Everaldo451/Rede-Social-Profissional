"""Repositórios em memória para testar as regras de negócio sem bancos."""
from collections import defaultdict
from itertools import count
from types import SimpleNamespace

_ids = count(1)


def new_id() -> str:
    return str(next(_ids))


class FakeUserRepository:
    def __init__(self):
        self.users = {}

    def add(self, name, headline=""):
        uid = new_id()
        self.users[uid] = {"id": uid, "name": name, "headline": headline, "email": f"{uid}@x.com"}
        return uid

    def get_by_id(self, user_id):
        return self.users.get(user_id)

    def get_many_by_ids(self, ids):
        return {i: self.users[i] for i in ids if i in self.users}


class FakePostRepository:
    def __init__(self):
        self.posts = {}
        self._order = count()

    def create(self, data):
        post = {**data, "id": new_id(), "_n": next(self._order)}
        self.posts[post["id"]] = post
        return dict(post)

    def get_by_id(self, post_id):
        post = self.posts.get(post_id)
        return dict(post) if post else None

    def _filtered(self, filters):
        posts = list(self.posts.values())
        if filters and filters.get("category"):
            posts = [p for p in posts if p["category"] == filters["category"]]
        if filters and filters.get("tag"):
            posts = [p for p in posts if filters["tag"] in p["tags"]]
        return sorted(posts, key=lambda p: (p["created_at"], p["_n"]), reverse=True)

    def get_paginated(self, offset, limit, filters=None):
        return [dict(p) for p in self._filtered(filters)[offset:offset + limit]]

    def count(self, filters=None):
        return len(self._filtered(filters))

    def list_all(self):
        return [dict(p) for p in self._filtered(None)]

    def update(self, post_id, data):
        self.posts[post_id].update(data)
        return True

    def delete(self, post_id):
        return self.posts.pop(post_id, None) is not None


class FakeCommentRepository:
    def __init__(self):
        self.comments = []

    def create(self, data):
        comment = {**data, "id": new_id()}
        self.comments.append(comment)
        return dict(comment)

    def list_by_post_ids(self, post_ids):
        grouped = defaultdict(list)
        for c in self.comments:
            if c["post_id"] in post_ids:
                grouped[c["post_id"]].append(dict(c))
        return grouped

    def delete_by_post(self, post_id):
        self.comments = [c for c in self.comments if c["post_id"] != post_id]


class FakeMediaRepository:
    def __init__(self):
        self.files = {}

    def save(self, filename, content_type, data):
        fid = new_id()
        self.files[fid] = {"filename": filename, "content_type": content_type, "data": data}
        return fid

    def get(self, file_id):
        return self.files.get(file_id)

    def delete(self, file_id):
        self.files.pop(file_id, None)


def post_data(text="Olá, TI!", **extra):
    """Imita um DTO já validado (os services só leem atributos)."""
    fields = {"text": text, "category": "Dica", "tags": [], "code": None,
              "code_language": "python", "remove_media_ids": [], **extra}
    return SimpleNamespace(**fields)


def comment_data(text="Boa!"):
    return SimpleNamespace(text=text)
