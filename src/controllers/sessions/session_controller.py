from pydantic import ValidationError

from dto.sessions.request.session_requests import (
    LoginRequest,
    RevokeSessionRequest,
    SessionIdRequest,
)
from dto.shared.response.base_response import BaseResponse


class SessionController:
    def __init__(self, session_service):
        self.service = session_service

    def login(self, data):
        try:
            request = LoginRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Informe um e-mail e uma senha válidos.")
        session_id = self.service.login(request.email, request.password)
        if session_id is None:
            return BaseResponse(status=False, message="E-mail ou senha inválidos.")
        return BaseResponse(status=True, data=session_id)

    def get_current_user(self, data):
        return self._session_operation(data, self.service.get_current_user)

    def get_all_sessions_for_current_user(self, data):
        return self._session_operation(data, self.service.get_all_sessions_for_current_user)

    def logout(self, data):
        return self._session_operation(data, self.service.logout)

    def revoke_other_session(self, data):
        try:
            request = RevokeSessionRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Referência de sessão inválida.")
        if not self.service.revoke_other_session(request.session_id, request.reference):
            return BaseResponse(status=False, message="A sessão selecionada não pode ser encerrada.")
        return BaseResponse(status=True, message="Sessão encerrada.")

    def _session_operation(self, data, operation):
        try:
            request = SessionIdRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Identificador de sessão inválido.")
        result = operation(request.session_id)
        if result is None or result is False:
            return BaseResponse(status=False, message="Sessão encerrada ou expirada.")
        return BaseResponse(status=True, data=result)
