# Camada de entrada das operações de curtidas; conecta a interface aos serviços.
from controllers.shared.response_handler import run
class LikeController:
    def __init__(self,service): self._service=service
    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self,user_id,post_id): return run(lambda:self._service.create(user_id,post_id))
    # Solicita ao serviço o registro identificado e devolve o resultado à interface.
    def get_by_id(self,like_id): return run(lambda:self._service.get_by_id(like_id))
    # Consulta as curtidas da publicação informada.
    def get_by_post_id(self,post_id): return run(lambda:self._service.get_by_post_id(post_id))
    # Encaminha a remoção da curtida do usuário nessa publicação.
    def delete_user_like(self,user_id,post_id): return run(lambda:self._service.delete_user_like(user_id,post_id))
    # Solicita a remoção do registro e devolve uma resposta à interface.
    def delete(self,like_id): return run(lambda:self._service.delete(like_id))
