from core.errors import NotFound, AuthenticationFailed
class LikeService:
    def __init__(self,repo,post_repository,user_repository,notification_service=None): self._repo=repo; self._posts=post_repository; self._users=user_repository; self._notifications=notification_service
    def create(self,user_id,post_id):
        if not self._users.get_by_id(user_id): raise AuthenticationFailed("Entre para curtir uma publicação.")
        if not self._posts.get_by_id(post_id): raise NotFound("Publicação não encontrada.")
        like=self._repo.create(user_id,post_id)
        post=self._posts.get_by_id(post_id)
        author=self._users.get_by_id(user_id)
        if self._notifications and post["author_id"] != user_id:
            self._notifications.create({"user_id":post["author_id"],"title":"Sua publicação recebeu uma curtida","message":f"{author['name']} curtiu sua publicação.","kind":"like"})
        return like
    def get_by_id(self,like_id):
        item=self._repo.get_by_id(like_id)
        if not item: raise NotFound("Curtida não encontrada.")
        return item
    def get_by_post_id(self,post_id): return self._repo.get_by_post_id(post_id)
    def delete_user_like(self,user_id,post_id): return self._repo.delete_user_like(user_id,post_id)
    def delete(self,like_id): return self._repo.delete(like_id)
