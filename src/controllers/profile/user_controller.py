# Camada de entrada das operações de usuários e seus perfis profissionais; conecta a interface aos serviços.
import logging

from pydantic import ValidationError

from common.errors import AppError
from dto.profile.request.skill_requests import (
    AddUserSkillRequest,
    UserSkillFiltersRequest,
    UserSkillRemovalRequest,
)
from dto.profile.request.user_requests import (
    EducationRemovalRequest,
    EducationRequest,
    ExperienceRemovalRequest,
    ExperienceRequest,
    MembershipRemovalRequest,
    MembershipRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserIdRequest,
    UserPaginationRequest,
    UserProfileRequest,
)
from dto.sessions.request.session_requests import LoginRequest
from dto.shared.response.base_response import BaseResponse

logger = logging.getLogger(__name__)


class UserController:
    def __init__(self, user_service):
        self.user_service = user_service

    # Valida o dicionário de entrada com o DTO e devolve o modelo ou uma resposta de erro.
    @staticmethod
    def _validate_request(request_model, data):
        try:
            return request_model.model_validate(data), None
        except ValidationError:
            return None, BaseResponse(
                status=False, message="Os dados informados são inválidos."
            )
        except AppError as error:
            return None, BaseResponse(status=False, message=str(error))

    # Executa a regra de negócio e padroniza o resultado; falhas inesperadas são registradas no log.
    @staticmethod
    def _run_service(action, success_message=None):
        try:
            return BaseResponse(
                status=True, data=action(), message=success_message
            )
        except (AppError, ValidationError) as error:
            return BaseResponse(status=False, message=str(error))
        except Exception:
            logger.exception("Falha inesperada ao executar uma operação de usuário.")
            return BaseResponse(
                status=False, message="Ocorreu um erro interno."
            )

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, data):
        request, error = self._validate_request(RegisterRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.create(request.model_dump()),
            "Conta criada com sucesso!",
        )

    # Solicita ao serviço o registro identificado e devolve o resultado à interface.
    def get_by_id(self, usuario_id, visualizador_id=None):
        """``visualizador_id`` é o usuário logado; define o que pode ver do perfil."""
        request, error = self._validate_request(
            UserProfileRequest,
            {"usuario_id": usuario_id, "visualizador_id": visualizador_id},
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.get_by_id(
                request.usuario_id, request.visualizador_id
            )
        )

    # Valida as credenciais recebidas e solicita a autenticação ao serviço de usuários.
    def authenticate(self, data):
        request, error = self._validate_request(LoginRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.authenticate(
                request.email, request.senha
            )
        )

    # Encaminha a consulta da lista completa ao serviço.
    def list_all(self):
        return self._run_service(self.user_service.list_all)

    # Encaminha posição inicial, tamanho da página e filtros para a consulta.
    def get_paginated(self, offset, limit, filters=None):
        request, error = self._validate_request(
            UserPaginationRequest,
            {"offset": offset, "limit": limit, "filters": filters},
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.get_paginated(
                request.offset, request.limit, request.filters
            )
        )

    # Encaminha a atualização ao serviço após validar os dados de entrada.
    def update(self, usuario_id, data):
        user_request, error = self._validate_request(
            UserIdRequest, {"usuario_id": usuario_id}
        )
        if error:
            return error
        request, error = self._validate_request(UpdateProfileRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.update(
                user_request.usuario_id,
                request.model_dump(exclude_unset=True),
            ),
            "Perfil atualizado com sucesso.",
        )

    # Solicita a remoção do registro e devolve uma resposta à interface.
    def delete(self, usuario_id):
        request, error = self._validate_request(
            UserIdRequest, {"usuario_id": usuario_id}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.delete(request.usuario_id),
            "Conta removida com sucesso.",
        )

    # Valida a experiência profissional e o usuário antes de encaminhar o cadastro.
    def add_experience(self, usuario_id, data):
        user_request, error = self._validate_request(
            UserIdRequest, {"usuario_id": usuario_id}
        )
        if error:
            return error
        request, error = self._validate_request(ExperienceRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.add_experience(
                user_request.usuario_id, request.model_dump()
            ),
            "Experiência adicionada com sucesso.",
        )

    # Valida os campos que identificam a experiência a remover.
    def remove_experience(
        self, usuario_id, organizacao_id, cargo, data_inicio
    ):
        request, error = self._validate_request(
            ExperienceRemovalRequest,
            {
                "usuario_id": usuario_id,
                "organizacao_id": organizacao_id,
                "cargo": cargo,
                "data_inicio": data_inicio,
            },
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.remove_experience(
                request.usuario_id,
                request.organizacao_id,
                request.cargo,
                request.data_inicio,
            ),
            "Experiência removida com sucesso.",
        )

    # Valida os dados de formação antes de associá-los ao usuário.
    def add_education(self, usuario_id, data):
        user_request, error = self._validate_request(
            UserIdRequest, {"usuario_id": usuario_id}
        )
        if error:
            return error
        request, error = self._validate_request(EducationRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.add_education(
                user_request.usuario_id, request.model_dump()
            ),
            "Formação adicionada com sucesso.",
        )

    # Valida os campos que identificam a formação a remover.
    def remove_education(
        self, usuario_id, instituicao_id, curso, grau
    ):
        request, error = self._validate_request(
            EducationRemovalRequest,
            {
                "usuario_id": usuario_id,
                "instituicao_id": instituicao_id,
                "curso": curso,
                "grau": grau,
            },
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.remove_education(
                request.usuario_id,
                request.instituicao_id,
                request.curso,
                request.grau,
            ),
            "Formação removida com sucesso.",
        )

    # Valida o vínculo com a organização e encaminha sua inclusão.
    def add_membership(self, usuario_id, data):
        user_request, error = self._validate_request(
            UserIdRequest, {"usuario_id": usuario_id}
        )
        if error:
            return error
        request, error = self._validate_request(MembershipRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.add_membership(
                user_request.usuario_id, request.model_dump()
            ),
            "Vínculo com a organização adicionado com sucesso.",
        )

    # Valida o usuário, a organização e o papel que identificam o vínculo a remover.
    def remove_membership(self, usuario_id, organizacao_id, papel):
        request, error = self._validate_request(
            MembershipRemovalRequest,
            {
                "usuario_id": usuario_id,
                "organizacao_id": organizacao_id,
                "papel": papel,
            },
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.remove_membership(
                request.usuario_id, request.organizacao_id, request.papel
            ),
            "Vínculo com a organização removido com sucesso.",
        )

    # Valida a habilidade e seus detalhes antes de associá-la ao perfil.
    def add_skill(
        self,
        usuario_id,
        habilidade_id,
        tipo,
        nivel=None,
        experiencia_anos=None,
        modalidade=None,
        disponibilidade=None,
    ):
        request, error = self._validate_request(
            AddUserSkillRequest,
            {
                "usuario_id": usuario_id,
                "habilidade_id": habilidade_id,
                "tipo": tipo,
                "nivel": nivel,
                "experiencia_anos": experiencia_anos,
                "modalidade": modalidade,
                "disponibilidade": disponibilidade,
            },
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.add_skill(
                request.usuario_id,
                request.habilidade_id,
                request.tipo,
                request.nivel,
                request.experiencia_anos,
                request.modalidade,
                request.disponibilidade,
            ),
            "Habilidade vinculada com sucesso.",
        )

    # Valida o tipo de relação e os identificadores antes de remover a habilidade do perfil.
    def remove_skill(self, usuario_id, habilidade_id, tipo):
        request, error = self._validate_request(
            UserSkillRemovalRequest,
            {
                "usuario_id": usuario_id,
                "habilidade_id": habilidade_id,
                "tipo": tipo,
            },
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.remove_skill(
                request.usuario_id, request.habilidade_id, request.tipo
            ),
            "Habilidade removida com sucesso.",
        )

    # Valida os filtros e solicita as habilidades associadas aos usuários.
    def get_skills(self, filters=None):
        request, error = self._validate_request(
            UserSkillFiltersRequest, filters or {}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.get_skills(
                request.model_dump(exclude_none=True)
            )
        )
