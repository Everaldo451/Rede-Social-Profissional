# Camada de entrada das operações de habilidades; conecta a interface aos serviços.
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
            logger.exception("Falha inesperada ao executar uma operação de habilidade.")
            return BaseResponse(
                status=False, message="Ocorreu um erro interno."
            )

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, data):
        request, error = self._validate_request(SkillRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.create(request.model_dump()),
            "Habilidade cadastrada com sucesso.",
        )

    # Solicita ao serviço o registro identificado e devolve o resultado à interface.
    def get_by_id(self, habilidade_id):
        request, error = self._validate_request(
            SkillIdRequest, {"habilidade_id": habilidade_id}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.get_by_id(request.habilidade_id)
        )

    # Valida os filtros e consulta um registro correspondente.
    def get_one(self, filters=None):
        request, error = self._validate_request(
            SkillFiltersRequest, {"filters": filters}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.skill_service.get_one(request.filters)
        )

    # Encaminha posição inicial, tamanho da página e filtros para a consulta.
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

    # Encaminha a atualização ao serviço após validar os dados de entrada.
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

    # Solicita a remoção do registro e devolve uma resposta à interface.
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
