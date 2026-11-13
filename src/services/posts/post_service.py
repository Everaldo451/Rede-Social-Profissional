from datetime import datetime, timezone

from common.errors import ForbiddenError, NotFoundError, UnauthorizedError
from common.presenters import author_view, comment_view

MAX_PAGE_SIZE = 50


class PostService:
    def __init__(self, post_repository, user_repository, comment_repository, media_service):
        self._posts = post_repository
        self._users = user_repository
        self._comments = comment_repository
        self._media = media_service

    # RF009 ---------------------------------------------------------------
    def create(self, author_id, data, files=()):
        if not self._users.get_by_id(author_id):
            raise UnauthorizedError("Você precisa estar autenticado para publicar.")
        post = self._posts.create(
            {
                "author_id": author_id,
                "text": data.text,
                "category": data.category,
                "tags": list(data.tags),
                "code": data.code,
                "code_language": data.code_language,
                "media": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
            }
        )
        media = []
        try:
            media = self._media.store_many(files, post["id"])
            if media and not self._posts.update(post["id"], {"media": media}):
                raise NotFoundError("A publicação não pôde ser salva.")
            post["media"] = media
        except Exception:
            self._media.delete_many([m["id"] for m in media])
            self._posts.delete(post["id"])
            raise
        return self._present_many([post])[0]

    # RF010 ---------------------------------------------------------------
    def update(self, requester_id, post_id, data, new_files=()):
        post = self._get_owned(requester_id, post_id)
        remove_ids = set(getattr(data, "remove_media_ids", None) or [])
        kept = [m for m in post["media"] if m["id"] not in remove_ids]
        removed = [m for m in post["media"] if m["id"] in remove_ids]
        added = self._media.store_many(
            new_files, post_id, already_attached=len(kept)
        )
        try:
            self._posts.update(
                post_id,
                {
                    "text": data.text,
                    "category": data.category,
                    "tags": list(data.tags),
                    "code": data.code,
                    "code_language": data.code_language,
                    "media": kept + added,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        except Exception:
            self._media.delete_many([m["id"] for m in added])
            raise
        self._media.delete_many([m["id"] for m in removed])
        return self.get_by_id(post_id)

    def delete(self, requester_id, post_id):
        post = self._get_owned(requester_id, post_id)
        self._comments.delete_by_post(post_id)
        self._posts.delete(post_id)
        self._media.delete_many([m["id"] for m in post["media"]])

    # RF011 ---------------------------------------------------------------
    def get_by_id(self, post_id):
        post = self._posts.get_by_id(post_id)
        if not post:
            raise NotFoundError("Publicação não encontrada.")
        return self._present_many([post])[0]

    def get_paginated(self, offset, limit, filters=None):
        offset = max(0, int(offset))
        limit = max(1, min(int(limit), MAX_PAGE_SIZE))
        posts = self._posts.get_paginated(offset, limit, filters)
        return {
            "items": self._present_many(posts),
            "total": self._posts.count(filters),
            "offset": offset,
            "limit": limit,
        }

    def list_all(self):
        return self._present_many(self._posts.list_all())

    # internos ------------------------------------------------------------
    def _get_owned(self, requester_id, post_id):
        post = self._posts.get_by_id(post_id)
        if not post:
            raise NotFoundError("Publicação não encontrada.")
        if post["author_id"] != requester_id:
            raise ForbiddenError("Você só pode editar ou excluir as suas próprias publicações.")
        post["media"] = self._post_media(post)
        return post

    def _present_many(self, posts):
        if not posts:
            return []
        comments = self._comments.list_by_post_ids([p["id"] for p in posts])
        user_ids = {p["author_id"] for p in posts}
        user_ids |= {c["author_id"] for group in comments.values() for c in group}
        users = self._users.get_many_by_ids(user_ids)
        return [
            {
                "id": p["id"],
                "text": p["text"],
                "category": p.get("category", "Dica"),
                "tags": p.get("tags", []),
                "code": p.get("code"),
                "code_language": p.get("code_language", "text"),
                "media": self._post_media(p),
                "created_at": p["created_at"],
                "updated_at": p.get("updated_at"),
                "author": author_view(users, p["author_id"]),
                "comments": [comment_view(users, c) for c in comments.get(p["id"], [])],
            }
            for p in posts
        ]

    def _post_media(self, post):
        stored_media = post.get("media") or []
        if stored_media:
            return stored_media
        files = self._media.list(
            {
                "proprietario_id": post["id"],
                "proprietario_tipo": "post",
                "tipo": "imagem_publicacao",
                "visibilidade": "publica",
            }
        )
        return [
            {
                "id": item["media_id"],
                "filename": item["filename"],
                "content_type": item["metadata"]["tipo_mime"],
            }
            for item in files
        ]
