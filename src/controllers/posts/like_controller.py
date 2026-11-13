from controllers.shared.response_handler import run
class LikeController:
    def __init__(self,service): self._service=service
    def create(self,user_id,post_id): return run(lambda:self._service.create(user_id,post_id))
    def get_by_id(self,like_id): return run(lambda:self._service.get_by_id(like_id))
    def get_by_post_id(self,post_id): return run(lambda:self._service.get_by_post_id(post_id))
    def delete_user_like(self,user_id,post_id): return run(lambda:self._service.delete_user_like(user_id,post_id))
    def delete(self,like_id): return run(lambda:self._service.delete(like_id))
