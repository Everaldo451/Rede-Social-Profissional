import logging

from pydantic import ValidationError

from common.errors import AppError
from dto.profile.request.skill_requests import (
    SkillFiltersRequest,
    SkillIdRequest,
    SkillPaginationRequest,
    SkillRequest,
    UpdateSkillRequest,
)
from dto.shared.response.base_response import BaseResponse

logger = logging.getLogger(__name__)


class SkillController:
    def __init__(self, skill_service):
        self.skill_service = skill_service

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
            logger.exception("Falha inesperada ao executar uma operação de habilidade.")
            return BaseResponse(
                status=False, message="Ocorreu um erro interno."
            )

    def create(self, data):
        request, error = self._validate_request(SkillRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.create(request.model_dump()),
            "Habilidade cadastrada com sucesso.",
        )

    def get_by_id(self, habilidade_id):
        request, error = self._validate_request(
            SkillIdRequest, {"habilidade_id": habilidade_id}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.get_by_id(request.habilidade_id)
        )

    def get_one(self, filters=None):
        request, error = self._validate_request(
            SkillFiltersRequest, {"filters": filters}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.get_one(request.filters)
        )

    def get_paginated(self, offset, limit, filters=None):
        request, error = self._validate_request(
            SkillPaginationRequest,
            {"offset": offset, "limit": limit, "filters": filters},
        )
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.get_paginated(
                request.offset, request.limit, request.filters
            )
        )

    def update(self, habilidade_id, data):
        id_request, error = self._validate_request(
            SkillIdRequest, {"habilidade_id": habilidade_id}
        )
        if error:
            return error
        request, error = self._validate_request(UpdateSkillRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.update(
                id_request.habilidade_id,
                request.model_dump(exclude_unset=True),
            ),
            "Habilidade atualizada com sucesso.",
        )

    def delete(self, habilidade_id):
        request, error = self._validate_request(
            SkillIdRequest, {"habilidade_id": habilidade_id}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.delete(request.habilidade_id),
            "Habilidade removida com sucesso.",
        )
