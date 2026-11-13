from controllers.shared.response_handler import run
from dto.posts.request.post_requests import CreatePostRequest, UpdatePostRequest


class PostController:
    def __init__(self, post_service):
        self._service = post_service

    def create(self, author_id, data: dict, files=()):
        return run(lambda: self._service.create(author_id, CreatePostRequest(**data), files))

    def get_by_id(self, post_id):
        return run(lambda: self._service.get_by_id(post_id))

    def get_paginated(self, offset, limit, filters=None):
        return run(lambda: self._service.get_paginated(offset, limit, filters))

    def list_all(self):
        return run(self._service.list_all)

    def update(self, requester_id, post_id, data: dict, new_files=()):
        return run(
            lambda: self._service.update(requester_id, post_id, UpdatePostRequest(**data), new_files)
        )

    def delete(self, requester_id, post_id):
        return run(lambda: self._service.delete(requester_id, post_id))
