# Camada de entrada das operações de mentorias; conecta a interface aos serviços.
from dto.connections.request.mentorship_requests import (
    CreateMentorshipRequest,
    MentorshipDecisionRequest,
)
from dto.connections.request.network_requests import ProfessionalSearchRequest

from ._response import run_action


class MentorshipController:
    def __init__(self, mentorship_service):
        self.service = mentorship_service

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, mentee_id, data):
        return run_action(
            lambda: self.service.create(
                mentee_id, CreateMentorshipRequest.model_validate(data).model_dump()
            )
        )

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def get_by_id(self, mentorship_id):
        pass

    # Valida a busca e repassa os limites da página ao serviço de mentoria.
    def filter_mentors(self, user_id, data, offset=0, limit=20):
        return run_action(
            lambda: self.service.filter_mentors(
                user_id,
                ProfessionalSearchRequest.model_validate(data),
                offset,
                limit,
            )
        )

    # Consulta os dados associados ao usuário por meio do serviço.
    def get_by_user_id(self, user_id):
        return run_action(self.service.get_by_user_id, user_id)

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def list_all(self):
        pass

    # Obtém as solicitações relacionadas ao usuário informado.
    def list_requests(self, user_id):
        return run_action(self.service.list_requests, user_id)

    # Encaminha a atualização ao serviço após validar os dados de entrada.
    def update(self, user_id, mentorship_id, data):
        return run_action(
            lambda: self.service.update(
                user_id,
                mentorship_id,
                MentorshipDecisionRequest.model_validate(data),
            )
        )

    # Método reservado: o corpo contém apenas pass e ainda não executa uma operação.
    def delete(self, mentorship_id):
        pass

    # Solicita uma página de mentores recomendados para o usuário.
    def recommend(self, user_id, offset=0, limit=20):
        return run_action(self.service.recommend, user_id, offset, limit)

    # Consulta os nomes das habilidades que o usuário deseja desenvolver.
    def desired_skills(self, user_id):
        return run_action(self.service.desired_skills, user_id)
