from pydantic import ValidationError

from dto.notifications.request.notification_requests import (
    CreateNotificationRequest,
    NotificationFiltersRequest,
    NotificationIdRequest,
    NotificationPaginationRequest,
    NotificationUserRequest,
    UpdateNotificationRequest,
)
from dto.shared.response.base_response import BaseResponse
from services.notifications.notification_service import (
    NotificationNotFoundError,
    NotificationPermissionError,
)


class NotificationController:
    def __init__(self, notification_service):
        self.notification_service = notification_service

    @staticmethod
    def _validation_error(error: ValidationError) -> BaseResponse:
        details = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        return BaseResponse(status=False, message=f"Dados inválidos: {details}")

    def create(self, data):
        try:
            request = CreateNotificationRequest.model_validate(data)
        except ValidationError as error:
            return self._validation_error(error)

        notification = self.notification_service.create(request.model_dump())
        return BaseResponse(
            status=True, data=notification, message="Notificação criada com sucesso."
        )

    def get_by_id(self, notification_id, user_id=None):
        try:
            request = NotificationIdRequest(notification_id=notification_id)
            if user_id is not None:
                user_id = NotificationUserRequest(user_id=user_id).user_id
        except ValidationError as error:
            return self._validation_error(error)

        try:
            notification = self.notification_service.get_by_id(
                request.notification_id, user_id
            )
        except (NotificationNotFoundError, NotificationPermissionError) as error:
            return BaseResponse(status=False, message=str(error))
        return BaseResponse(status=True, data=notification)

    def get_paginated(self, offset, limit, filters=None):
        try:
            pagination = NotificationPaginationRequest(offset=offset, limit=limit)
            validated_filters = NotificationFiltersRequest.model_validate(filters or {})
        except ValidationError as error:
            return self._validation_error(error)

        notifications = self.notification_service.get_paginated(
            pagination.offset,
            pagination.limit,
            validated_filters.model_dump(exclude_none=True),
        )
        return BaseResponse(status=True, data=notifications)

    def count_unread_by_user_id(self, user_id):
        try:
            request = NotificationUserRequest(user_id=user_id)
        except ValidationError as error:
            return self._validation_error(error)

        total = self.notification_service.count_unread_by_user_id(request.user_id)
        return BaseResponse(status=True, data=total)

    def mark_all_as_read(self, user_id):
        try:
            request = NotificationUserRequest(user_id=user_id)
        except ValidationError as error:
            return self._validation_error(error)

        updated = self.notification_service.mark_all_as_read(request.user_id)
        return BaseResponse(
            status=True,
            data=updated,
            message="Todas as notificações foram marcadas como lidas.",
        )

    def update(self, notification_id, data, user_id=None):
        try:
            request_id = NotificationIdRequest(notification_id=notification_id)
            request_data = UpdateNotificationRequest.model_validate(data)
            if user_id is not None:
                user_id = NotificationUserRequest(user_id=user_id).user_id
        except ValidationError as error:
            return self._validation_error(error)

        try:
            notification = self.notification_service.update(
                request_id.notification_id, request_data.model_dump(), user_id
            )
        except (NotificationNotFoundError, NotificationPermissionError) as error:
            return BaseResponse(status=False, message=str(error))
        return BaseResponse(
            status=True, data=notification, message="Notificação atualizada."
        )

    def delete(self, notification_id, user_id=None):
        try:
            request = NotificationIdRequest(notification_id=notification_id)
            if user_id is not None:
                user_id = NotificationUserRequest(user_id=user_id).user_id
        except ValidationError as error:
            return self._validation_error(error)

        try:
            self.notification_service.delete(request.notification_id, user_id)
        except (NotificationNotFoundError, NotificationPermissionError) as error:
            return BaseResponse(status=False, message=str(error))
        return BaseResponse(status=True, message="Notificação excluída.")
