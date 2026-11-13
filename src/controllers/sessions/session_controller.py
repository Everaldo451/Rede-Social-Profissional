# Camada de entrada das operações de sessões autenticadas; conecta a interface aos serviços.
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

    # Valida e-mail e senha, solicita o login e devolve o identificador da sessão criada.
    def login(self, data):
        try:
            request = LoginRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Informe um e-mail e uma senha válidos.")
        session_id = self.service.login(request.email, request.senha)
        if session_id is None:
            return BaseResponse(status=False, message="E-mail ou senha inválidos.")
        return BaseResponse(status=True, data=session_id)

    # Consulta o usuário da sessão por meio do tratamento comum de operações autenticadas.
    def get_current_user(self, data):
        return self._session_operation(data, self.service.get_current_user)

    # Obtém as sessões do usuário autenticado pela sessão apresentada.
    def get_all_sessions_for_current_user(self, data):
        return self._session_operation(data, self.service.get_all_sessions_for_current_user)

    # Solicita o encerramento da sessão usando a mesma validação das demais operações.
    def logout(self, data):
        return self._session_operation(data, self.service.logout)

    # Valida a referência de outra sessão e solicita seu encerramento.
    def revoke_other_session(self, data):
        try:
            request = RevokeSessionRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Referência de sessão inválida.")
        if not self.service.revoke_other_session(request.session_id, request.reference):
            return BaseResponse(status=False, message="A sessão selecionada não pode ser encerrada.")
        return BaseResponse(status=True, message="Sessão encerrada.")

    # Valida a sessão e converte resultados ausentes ou falsos em mensagem de expiração.
    def _session_operation(self, data, operation):
        try:
            request = SessionIdRequest.model_validate(data)
        except ValidationError:
            return BaseResponse(status=False, message="Identificador de sessão inválido.")
        result = operation(request.session_id)
        if result is None or result is False:
            return BaseResponse(status=False, message="Sessão encerrada ou expirada.")
        return BaseResponse(status=True, data=result)
