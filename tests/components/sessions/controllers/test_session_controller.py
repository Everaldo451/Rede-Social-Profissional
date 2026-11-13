# Testes de validação de login e da atualização de presença pela sessão autenticada.
from unittest.mock import Mock

from controllers.sessions.online_presence_controller import (
    OnlinePresenceController,
)
from controllers.sessions.session_controller import SessionController


# Confere as credenciais validadas encaminhadas ao serviço de sessão.
def test_login_passes_validated_login_request_to_service():
    service = Mock()
    service.login.return_value = "session-token"

    response = SessionController(service).login(
        {"email": "ana@example.com", "senha": "secret"}
    )

    assert response.status is True
    assert response.data == "session-token"
    service.login.assert_called_once_with("ana@example.com", "secret")


# Verifica a atualização periódica de presença para uma sessão autenticada.
def test_presence_heartbeat_updates_last_seen_for_authenticated_session():
    service = Mock()
    service.update_last_seen.return_value = True

    response = OnlinePresenceController(service).update_last_seen(
        {"session_id": "session-token"}
    )

    assert response.status is True
    service.update_last_seen.assert_called_once_with("session-token")
