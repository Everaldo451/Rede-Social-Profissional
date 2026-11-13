# Camada de entrada das operações de mídias; conecta a interface aos serviços.
import logging
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from dto.shared.request.media_requests import (
    MediaCreateRequest,
    MediaFiltersRequest,
    MediaIdRequest,
    MediaUpdateRequest,
)
from dto.shared.response.base_response import BaseResponse
from services.shared.media_errors import (
    MediaPersistenceError,
    MediaValidationError,
)
from services.shared.media_service import MediaFile


logger = logging.getLogger(__name__)


class MediaController:
    def __init__(self, media_service):
        self.media_service = media_service

    # Encaminha o cadastro ao serviço e apresenta seu resultado em uma resposta padronizada.
    def create(self, data):
        try:
            request = MediaCreateRequest.model_validate(data)
        except ValidationError as error:
            return self._validation_error(error)
        return self._execute(
            lambda: self.media_service.create(request.model_dump()),
            success_message="Mídia criada com sucesso.",
        )

    # Encaminha o arquivo para validação e gravação como foto do perfil.
    def create_profile_image(self, file: MediaFile, owner_id: str):
        return self._execute(
            lambda: self.media_service.create_profile_image(file, owner_id),
            success_message="Foto de perfil atualizada.",
        )

    # Solicita ao serviço o registro identificado e devolve o resultado à interface.
    def get_by_id(self, media_id):
        try:
            request = MediaIdRequest(media_id=media_id)
        except ValidationError as error:
            return self._validation_error(error)
        return self._execute(
            lambda: self.media_service.get_by_id(request.media_id),
            not_found_message="Mídia não encontrada.",
        )

    # Valida os filtros e consulta um registro correspondente.
    def get_one(self, filters=None):
        try:
            request = MediaFiltersRequest(filters=filters)
        except ValidationError as error:
            return self._validation_error(error)
        return self._execute(
            lambda: self.media_service.get_one(request.filters),
            not_found_message="Mídia não encontrada.",
        )

    # Valida os filtros e solicita a lista de mídias correspondente.
    def list(self, filters=None):
        try:
            request = MediaFiltersRequest(filters=filters)
        except ValidationError as error:
            return self._validation_error(error)
        return self._execute(
            lambda: self.media_service.list(request.filters),
        )

    # Encaminha a atualização ao serviço após validar os dados de entrada.
    def update(self, media_id, data):
        try:
            id_request = MediaIdRequest(media_id=media_id)
            update_request = MediaUpdateRequest.model_validate(data)
        except ValidationError as error:
            return self._validation_error(error)
        return self._execute(
            lambda: self.media_service.update(
                id_request.media_id,
                update_request.model_dump(exclude_unset=True, exclude_none=True),
            ),
            success_message="Mídia atualizada com sucesso.",
            not_found_message="Mídia não encontrada.",
        )

    # Solicita a remoção do registro e devolve uma resposta à interface.
    def delete(self, media_id):
        try:
            request = MediaIdRequest(media_id=media_id)
        except ValidationError as error:
            return self._validation_error(error)
        return self._execute(
            lambda: self.media_service.delete(request.media_id),
            success_message="Mídia excluída com sucesso.",
            not_found_message="Mídia não encontrada.",
            false_is_not_found=True,
        )

    # Padroniza sucesso, ausência de mídia e erros de validação ou persistência.
    @staticmethod
    def _execute(
        operation: Callable[[], Any],
        success_message: str | None = None,
        not_found_message: str | None = None,
        false_is_not_found: bool = False,
    ) -> BaseResponse:
        try:
            result = operation()
        except MediaValidationError as error:
            return BaseResponse(status=False, message=f"Dados inválidos: {error}")
        except MediaPersistenceError:
            logger.exception("A media persistence operation failed")
            return BaseResponse(
                status=False,
                message="Não foi possível concluir a operação de mídia. Tente novamente.",
            )

        if result is None or (false_is_not_found and result is False):
            return BaseResponse(status=False, message=not_found_message)
        return BaseResponse(status=True, data=result, message=success_message)

    # Transforma os erros de validação em uma resposta que a interface pode apresentar.
    @staticmethod
    def _validation_error(error: ValidationError) -> BaseResponse:
        return BaseResponse(status=False, message=f"Dados inválidos: {error}")
