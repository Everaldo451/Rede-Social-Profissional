from pydantic import ValidationError

from dto.sessions.request.session_requests import SessionIdRequest, UserIdRequest
from dto.shared.response.base_response import BaseResponse


class OnlinePresenceController:
    def __init__(self, online_presence_service):
        self.service = online_presence_service

    def get_online_users(self, data, user_ids, *, activity=False):
        try:
            session = SessionIdRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Identificador de sessão inválido.")
        online = self.service.get_online_users(session.session_id, user_ids, activity=activity)
        if online is None:
            return BaseResponse(status=False, message="Sessão encerrada ou expirada.")
        return BaseResponse(status=True, data=online)

    def get_by_user_id(self, data, *, activity=True):
        try:
            session = SessionIdRequest.model_validate(data)
            user = UserIdRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Informe um identificador de usuário válido.")
        online = self.service.get_by_user_id(
            session.session_id, user.user_id, activity=activity
        )
        if online is None:
            return BaseResponse(status=False, message="Sessão encerrada ou expirada.")
        return BaseResponse(status=True, data=online)

    def update_last_seen(self, data):
        try:
            session = SessionIdRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Identificador de sessão inválido.")
        if not self.service.update_last_seen(session.session_id):
            return BaseResponse(status=False, message="Sessão encerrada ou expirada.")
        return BaseResponse(status=True)
