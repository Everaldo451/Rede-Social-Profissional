# Camada de entrada das operações de organizações; conecta a interface aos serviços.
import logging

from pydantic import ValidationError

from common.errors import AppError
from dto.profile.request.organization_requests import (
    OrganizationCreatorRequest,
    OrganizationIdRequest,
    OrganizationPaginationRequest,
    OrganizationRequest,
    UpdateOrganizationRequest,
)
from dto.shared.response.base_response import BaseResponse

logger = logging.getLogger(__name__)


class OrganizationController:
    def __init__(self, organization_service):
        self.organization_service = organization_service

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
            logger.exception(
                "Falha inesperada ao executar uma operação de organização."
            )
            return BaseResponse(
                status=False, message="Ocorreu um erro interno."
            )

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, data, criado_por_usuario_id=None):
        request, error = self._validate_request(OrganizationRequest, data)
        if error:
            return error
        creator_id = None
        if criado_por_usuario_id is not None:
            creator_request, error = self._validate_request(
                OrganizationCreatorRequest,
                {"usuario_id": criado_por_usuario_id},
            )
            if error:
                return error
            creator_id = creator_request.usuario_id
        return self._run_service(
            lambda: self.organization_service.create(
                request.model_dump(exclude_none=True), creator_id
            ),
            "Organização cadastrada com sucesso.",
        )

    # Solicita ao serviço o registro identificado e devolve o resultado à interface.
    def get_by_id(self, organizacao_id):
        request, error = self._validate_request(
            OrganizationIdRequest, {"organizacao_id": organizacao_id}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.organization_service.get_by_id(request.organizacao_id)
        )

    # Encaminha posição inicial, tamanho da página e filtros para a consulta.
    def get_paginated(self, offset, limit, filters=None):
        request, error = self._validate_request(
            OrganizationPaginationRequest,
            {"offset": offset, "limit": limit, "filters": filters},
        )
        if error:
            return error
        return self._run_service(
            lambda: self.organization_service.get_paginated(
                request.offset, request.limit, request.filters
            )
        )

    # Encaminha a consulta da lista completa ao serviço.
    def list_all(self):
        return self._run_service(self.organization_service.list_all)

    # Encaminha a atualização ao serviço após validar os dados de entrada.
    def update(self, organizacao_id, data):
        id_request, error = self._validate_request(
            OrganizationIdRequest, {"organizacao_id": organizacao_id}
        )
        if error:
            return error
        request, error = self._validate_request(UpdateOrganizationRequest, data)
        if error:
            return error
        return self._run_service(
            lambda: self.organization_service.update(
                id_request.organizacao_id,
                request.model_dump(exclude_unset=True),
            ),
            "Organização atualizada com sucesso.",
        )

    # Solicita a remoção do registro e devolve uma resposta à interface.
    def delete(self, organizacao_id):
        request, error = self._validate_request(
            OrganizationIdRequest, {"organizacao_id": organizacao_id}
        )
        if error:
            return error
        return self._run_service(
            lambda: self.organization_service.delete(request.organizacao_id),
            "Organização removida com sucesso.",
        )
