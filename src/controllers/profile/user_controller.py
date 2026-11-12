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

    def create(self, data):
        request, error = self._validate_request(RegisterRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.create(request.model_dump()),
            "Conta criada com sucesso!",
        )

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

    def authenticate(self, data):
        request, error = self._validate_request(LoginRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.user_service.authenticate(
                request.email, request.senha
            )
        )

    def list_all(self):
        return self._run_service(self.user_service.list_all)

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
