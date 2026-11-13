import unittest
from unittest.mock import Mock

from common.errors import ForbiddenError, NotFoundError, UnauthorizedError
from services.posts.comment_service import CommentService
from services.posts.like_service import LikeService
from services.posts.post_service import PostService
from services.shared.media_errors import MediaValidationError
from services.shared.media_service import MAX_FILES, MediaFile, MediaService

from .fakes import (FakeCommentRepository, FakeMediaRepository, FakePostRepository,
                    FakeUserRepository, comment_data, post_data)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.users = FakeUserRepository()
        self.posts = FakePostRepository()
        self.comments = FakeCommentRepository()
        self.media_repo = FakeMediaRepository()
        self.media = MediaService(self.media_repo)
        self.notifications = Mock()
        self.post_service = PostService(self.posts, self.users, self.comments, self.media)
        self.comment_service = CommentService(
            self.comments,
            self.posts,
            self.users,
            notification_service=self.notifications,
        )
        self.ana = self.users.add("Ana", "Dev Python")
        self.bruno = self.users.add("Bruno", "DevOps")


class TestCreatePost(BaseCase):  # RF009
    def test_creates_text_post_with_author(self):
        post = self.post_service.create(self.ana, post_data("Primeiro post"))
        self.assertEqual(post["text"], "Primeiro post")
        self.assertEqual(post["author"]["name"], "Ana")
        self.assertIsNone(post["updated_at"])

    def test_requires_authenticated_user(self):
        with self.assertRaises(UnauthorizedError):
            self.post_service.create("inexistente", post_data())

    def test_stores_media(self):
        post = self.post_service.create(self.ana, post_data(), [MediaFile("a.png", "image/png", PNG)])
        self.assertEqual(len(post["media"]), 1)
        self.assertEqual(len(self.media_repo.files), 1)

    def test_rejects_disallowed_type_and_stores_nothing(self):
        with self.assertRaises(MediaValidationError):
            self.post_service.create(self.ana, post_data(), [MediaFile("x.exe", "application/x-msdownload", b"MZ")])
        self.assertEqual(self.posts.posts, {})

    def test_rejects_file_whose_content_does_not_match_type(self):
        with self.assertRaises(MediaValidationError):
            self.post_service.create(self.ana, post_data(), [MediaFile("a.png", "image/png", b"nao sou png")])

    def test_rejects_too_many_files(self):
        files = [MediaFile(f"{i}.png", "image/png", PNG) for i in range(MAX_FILES + 1)]
        with self.assertRaises(MediaValidationError):
            self.post_service.create(self.ana, post_data(), files)
        self.assertEqual(self.media_repo.files, {})


class TestEditDeletePost(BaseCase):  # RF010
    def setUp(self):
        super().setUp()
        self.post = self.post_service.create(self.ana, post_data("Original"), [MediaFile("a.png", "image/png", PNG)])

    def test_owner_can_edit(self):
        updated = self.post_service.update(self.ana, self.post["id"], post_data("Editado", category="Projeto"))
        self.assertEqual(updated["text"], "Editado")
        self.assertEqual(updated["category"], "Projeto")
        self.assertIsNotNone(updated["updated_at"])
        self.assertEqual(len(updated["media"]), 1)  # mídia mantida

    def test_edit_can_remove_and_add_media(self):
        old_id = self.post["media"][0]["id"]
        updated = self.post_service.update(
            self.ana, self.post["id"], post_data("x", remove_media_ids=[old_id]),
            [MediaFile("b.png", "image/png", PNG)],
        )
        self.assertEqual([m["filename"] for m in updated["media"]], ["b.png"])
        self.assertNotIn(old_id, self.media_repo.files)

    def test_other_user_cannot_edit(self):
        with self.assertRaises(ForbiddenError):
            self.post_service.update(self.bruno, self.post["id"], post_data("Hack"))
        self.assertEqual(self.posts.posts[self.post["id"]]["text"], "Original")

    def test_other_user_cannot_delete(self):
        with self.assertRaises(ForbiddenError):
            self.post_service.delete(self.bruno, self.post["id"])
        self.assertIn(self.post["id"], self.posts.posts)

    def test_owner_delete_removes_post_comments_and_media(self):
        self.comment_service.create(self.bruno, self.post["id"], comment_data())
        self.post_service.delete(self.ana, self.post["id"])
        self.assertEqual(self.posts.posts, {})
        self.assertEqual(self.comments.comments, [])
        self.assertEqual(self.media_repo.files, {})

    def test_missing_post(self):
        with self.assertRaises(NotFoundError):
            self.post_service.delete(self.ana, "999")


class TestFeed(BaseCase):  # RF011
    def test_newest_first_with_author_and_date(self):
        self.post_service.create(self.ana, post_data("antigo"))
        self.post_service.create(self.bruno, post_data("novo"))
        feed = self.post_service.get_paginated(0, 10)
        self.assertEqual([p["text"] for p in feed["items"]], ["novo", "antigo"])
        self.assertEqual(feed["items"][0]["author"]["name"], "Bruno")
        self.assertIsNotNone(feed["items"][0]["created_at"])
        self.assertEqual(feed["total"], 2)

    def test_pagination_and_filters(self):
        for i in range(5):
            self.post_service.create(self.ana, post_data(f"p{i}", category="Vaga" if i == 0 else "Dica", tags=["python"]))
        page = self.post_service.get_paginated(2, 2)
        self.assertEqual(len(page["items"]), 2)
        self.assertEqual(page["total"], 5)
        self.assertEqual(self.post_service.get_paginated(0, 10, {"category": "Vaga"})["total"], 1)
        self.assertEqual(self.post_service.get_paginated(0, 10, {"tag": "java"})["total"], 0)

    def test_deleted_author_is_tolerated(self):
        self.post_service.create(self.ana, post_data())
        del self.users.users[self.ana]
        self.assertEqual(self.post_service.get_paginated(0, 10)["items"][0]["author"]["name"], "Usuário removido")


class TestComments(BaseCase):  # RF012
    def setUp(self):
        super().setUp()
        self.post = self.post_service.create(self.ana, post_data())

    def test_other_user_can_comment(self):
        comment = self.comment_service.create(self.bruno, self.post["id"], comment_data("Ótimo!"))
        self.assertEqual(comment["author"]["name"], "Bruno")
        feed = self.post_service.get_paginated(0, 10)
        self.assertEqual(feed["items"][0]["comments"][0]["text"], "Ótimo!")
        self.notifications.create.assert_called_once_with(
            {
                "destinatario_id": self.ana,
                "tipo": "comentario",
                "titulo": "Bruno comentou sua publicação",
                "referencia_tipo": "post",
                "referencia_id": self.post["id"],
            }
        )

    def test_author_cannot_comment_own_post(self):
        with self.assertRaises(ForbiddenError):
            self.comment_service.create(self.ana, self.post["id"], comment_data())

    def test_self_comment_can_be_enabled(self):
        service = CommentService(self.comments, self.posts, self.users, allow_self_comment=True)
        service.create(self.ana, self.post["id"], comment_data())

    def test_comment_on_missing_post(self):
        with self.assertRaises(NotFoundError):
            self.comment_service.create(self.bruno, "999", comment_data())

    def test_requires_authenticated_user(self):
        with self.assertRaises(UnauthorizedError):
            self.comment_service.create("fantasma", self.post["id"], comment_data())


class TestLikes(BaseCase):
    def test_like_notifies_post_author_once(self):
        post = self.post_service.create(self.ana, post_data())
        repository = Mock()
        likes = []
        repository.get_by_post_id.side_effect = lambda _: likes

        def create_like(user_id, post_id):
            like = {"user_id": user_id, "post_id": post_id}
            likes.append(like)
            return like

        repository.create.side_effect = create_like
        service = LikeService(
            repository,
            self.posts,
            self.users,
            notification_service=self.notifications,
        )

        service.create(self.bruno, post["id"])
        service.create(self.bruno, post["id"])

        self.assertEqual(repository.create.call_count, 2)
        self.notifications.create.assert_called_once_with(
            {
                "destinatario_id": self.ana,
                "tipo": "curtida",
                "titulo": "Bruno curtiu sua publicação",
                "referencia_tipo": "post",
                "referencia_id": post["id"],
            }
        )


if __name__ == "__main__":
    unittest.main()
